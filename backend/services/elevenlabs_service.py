"""
ElevenLabs TTS Service
Convierte texto a audio usando ElevenLabs API.
"""
import base64
from typing import Optional
from loguru import logger
from elevenlabs.client import ElevenLabs
from backend.config import get_business_settings


class ElevenLabsService:
    """Servicio de Text-to-Speech con ElevenLabs."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Inicializa el servicio.

        Args:
            api_key: API key de ElevenLabs (se lee de settings si no se provee)
        """
        settings = get_business_settings()
        self.api_key = api_key or settings.elevenlabs_api_key

        if not self.api_key:
            logger.warning(" ElevenLabs API key no configurado - TTS deshabilitado")
            self.enabled = False
            self.client = None
        else:
            self.enabled = True
            self.client = ElevenLabs(api_key=self.api_key)
            logger.info(" ElevenLabs TTS habilitado")

        # Voz por defecto (se puede configurar en settings)
        self.default_voice_id = settings.elevenlabs_voice_id

    async def text_to_speech(
        self,
        text: str,
        voice_id: Optional[str] = None,
        model_id: str = "eleven_multilingual_v2",
        output_format: str = "mp3_44100_128"
    ) -> Optional[bytes]:
        """
        Convierte texto a audio.

        Args:
            text: Texto a convertir (max 5000 chars con plan free)
            voice_id: ID de voz (usa default si no se especifica)
            model_id: Modelo de ElevenLabs
                - "eleven_multilingual_v2": Soporta español, alta calidad
                - "eleven_turbo_v2": Más rápido pero menos natural
            output_format: Formato de salida (mp3_44100_128 por defecto)

        Returns:
            Audio bytes en formato MP3, o None si hay error
        """
        if not self.enabled or not self.client:
            logger.debug("TTS deshabilitado, retornando None")
            return None

        # Truncar texto si es muy largo (límite API)
        if len(text) > 5000:
            logger.warning(f"Texto muy largo ({len(text)} chars), truncando a 5000")
            text = text[:4997] + "..."

        voice_id = voice_id or self.default_voice_id

        try:
            logger.info(f" Generando audio con ElevenLabs ({len(text)} chars, voz={voice_id})")

            # Usar el SDK oficial de ElevenLabs
            audio_response = self.client.text_to_speech.convert(
                text=text,
                voice_id=voice_id,
                model_id=model_id,
                output_format=output_format,
            )

            # El SDK puede retornar un iterador de bytes o un objeto con atributos
            # Intentamos diferentes métodos de extracción
            logger.debug(" Convirtiendo respuesta de audio a bytes...")

            # Si es un iterador/generador, convertir a bytes
            if hasattr(audio_response, '__iter__'):
                try:
                    audio_bytes = b"".join(chunk for chunk in audio_response if isinstance(chunk, bytes))
                except Exception as iter_err:
                    logger.debug(f"No pudo iterar directamente: {iter_err}")
                    # Intentar como string/bytes directo
                    if isinstance(audio_response, bytes):
                        audio_bytes = audio_response
                    else:
                        # Último recurso: convertir a string y luego a bytes
                        audio_bytes = bytes(audio_response)
            else:
                # Si no es iterable, asumir que es bytes directo
                audio_bytes = bytes(audio_response)

            logger.info(f"✅ Audio generado: {len(audio_bytes)} bytes")
            return audio_bytes

        except TypeError as e:
            logger.error(f" TypeError en ElevenLabs (posible incompatibilidad SDK): {e}", exc_info=True)
            logger.error(f"   Tipo de respuesta: {type(audio_response) if 'audio_response' in locals() else 'unknown'}")
            return None
        except Exception as e:
            error_msg = str(e)

            # Detectar errores específicos de la API
            if "401" in error_msg or "Unusual activity detected" in error_msg:
                logger.error(f" API KEY BLOQUEADA por ElevenLabs: {error_msg[:200]}")
            elif "403" in error_msg or "quota" in error_msg.lower():
                logger.error(f" CUOTA EXCEDIDA en ElevenLabs: {error_msg[:200]}")
            else:
                logger.error(f" Error generando audio con ElevenLabs: {type(e).__name__}: {error_msg[:200]}")

            return None

    def audio_to_data_url(self, audio_bytes: bytes) -> str:
        """
        Convierte audio bytes a data URL para embedding en HTML.

        Args:
            audio_bytes: Audio en formato MP3

        Returns:
            Data URL: "data:audio/mpeg;base64,..."
        """
        base64_audio = base64.b64encode(audio_bytes).decode('utf-8')
        return f"data:audio/mpeg;base64,{base64_audio}"

    async def get_available_voices(self) -> list[dict]:
        """
        Obtiene lista de voces disponibles en ElevenLabs.

        Returns:
            Lista de diccionarios con info de voces: {voice_id, name, category, description}
        """
        if not self.enabled or not self.client:
            return []

        try:
            voices_response = self.client.voices.get_all()
            voices = []

            for voice in voices_response.voices:
                voices.append({
                    "voice_id": voice.voice_id,
                    "name": voice.name,
                    "category": getattr(voice, "category", "unknown"),
                    "description": getattr(voice, "description", "")
                })

            logger.info(f" Obtenidas {len(voices)} voces de ElevenLabs")
            return voices
        except Exception as e:
            logger.error(f" Error obteniendo voces: {e}")
            return []
