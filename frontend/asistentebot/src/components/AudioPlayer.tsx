/**
 * AudioPlayer - Componente para reproducir audio de mensajes del bot
 * Reproduce automáticamente al montarse
 */
import React, { useEffect, useRef, useState } from 'react';
import './AudioPlayer.css';

interface AudioPlayerProps {
  audioUrl: string;
  autoPlay?: boolean;
  onEnded?: () => void;
  onError?: (error: Error) => void;
}

export const AudioPlayer: React.FC<AudioPlayerProps> = ({
  audioUrl,
  autoPlay = true,
  onEnded,
  onError
}) => {
  const audioRef = useRef<HTMLAudioElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [hasError, setHasError] = useState(false);

  // Debug: log cuando se monta el componente
  console.log('🎵 AudioPlayer montado:', {
    audioUrlLength: audioUrl.length,
    autoPlay,
    isDataUrl: audioUrl.startsWith('data:')
  });

  useEffect(() => {
    console.log('🔧 useEffect ejecutado, audioRef.current:', audioRef.current);

    const audio = audioRef.current;
    if (!audio) {
      console.error('❌ audioRef.current es null!');
      return;
    }

    console.log('✅ Audio element encontrado, configurando...');

    // Handler cuando el audio está listo para reproducirse
    const handleCanPlay = () => {
      console.log('✅ Audio listo para reproducir (canplay)');
      setIsLoading(false);

      // Intentar auto-play si está habilitado
      if (autoPlay) {
        audio.play()
          .then(() => {
            console.log('✅ Audio reproduciéndose');
            setIsPlaying(true);
          })
          .catch((err) => {
            console.warn('⚠️ Auto-play bloqueado por el navegador:', err.name);
            // No marcar como error, solo mostrar botón de play manual
            setIsPlaying(false);
          });
      }
    };

    const handleLoadedMetadata = () => {
      console.log('📊 Metadata cargada, duración:', audio.duration);
    };

    const handleLoadStart = () => {
      console.log('🔄 Iniciando carga de audio...');
    };

    const handleProgress = () => {
      console.log('📥 Progreso de carga...');
    };

    // Timeout de seguridad: si después de 3 segundos no cargó, mostrar botón
    const loadTimeout = setTimeout(() => {
      if (isLoading) {
        console.warn('⏱️ Timeout: Audio tardó mucho en cargar, mostrando botón manual');
        setIsLoading(false);
      }
    }, 3000);

    audio.addEventListener('canplay', handleCanPlay);
    audio.addEventListener('loadedmetadata', handleLoadedMetadata);
    audio.addEventListener('loadstart', handleLoadStart);
    audio.addEventListener('progress', handleProgress);

    // Forzar carga
    audio.load();

    // Cleanup
    return () => {
      clearTimeout(loadTimeout);
      audio.removeEventListener('canplay', handleCanPlay);
      audio.removeEventListener('loadedmetadata', handleLoadedMetadata);
      audio.removeEventListener('loadstart', handleLoadStart);
      audio.removeEventListener('progress', handleProgress);
      audio.pause();
      audio.currentTime = 0;
    };
  }, [audioUrl, autoPlay, isLoading]);

  const handlePlay = () => {
    audioRef.current?.play();
    setIsPlaying(true);
  };

  const handlePause = () => {
    audioRef.current?.pause();
    setIsPlaying(false);
  };

  const handleEnded = () => {
    setIsPlaying(false);
    onEnded?.();
  };

  const handleError = (e: React.SyntheticEvent<HTMLAudioElement, Event>) => {
    const audioElement = e.currentTarget;
    console.error('❌ Error del elemento audio:', {
      error: audioElement.error,
      code: audioElement.error?.code,
      message: audioElement.error?.message,
      networkState: audioElement.networkState,
      readyState: audioElement.readyState
    });
    setHasError(true);
    setIsLoading(false);
    onError?.(new Error(`Failed to load audio: ${audioElement.error?.message || 'unknown error'}`));
  };

  return (
    <div className="audio-player">
      {/* Elemento audio SIEMPRE renderizado (oculto) */}
      <audio
        ref={audioRef}
        src={audioUrl}
        onEnded={handleEnded}
        onError={handleError}
        style={{ display: 'none' }}
      />

      {/* Estado: Error */}
      {hasError && (
        <div className="audio-player-error">
          <span className="audio-error-icon">⚠️</span>
          <span className="audio-error-text">Audio no disponible</span>
        </div>
      )}

      {/* Estado: Cargando */}
      {isLoading && !hasError && (
        <div className="audio-player-loading">
          <span className="audio-loading-icon">⏳</span>
          <span className="audio-loading-text">Cargando audio...</span>
        </div>
      )}

      {/* Estado: Reproduciendo */}
      {isPlaying && !isLoading && !hasError && (
        <div className="audio-indicator">
          <span className="audio-wave">🔊</span>
          <span className="audio-text">Reproduciendo...</span>
        </div>
      )}

      {/* Estado: Listo para reproducir (botón manual) */}
      {!isPlaying && !isLoading && !hasError && (
        <button
          className="audio-play-button"
          onClick={handlePlay}
          aria-label="Reproducir audio"
          title="Click para escuchar"
        >
          ▶️ <span className="audio-play-text">Escuchar</span>
        </button>
      )}
    </div>
  );
};
