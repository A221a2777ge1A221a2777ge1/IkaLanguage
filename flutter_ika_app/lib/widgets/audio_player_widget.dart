import 'package:flutter/material.dart';
import 'package:just_audio/just_audio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Audio player state provider
final audioPlayerProvider = StateNotifierProvider<AudioPlayerNotifier, AudioPlayerState>((ref) {
  return AudioPlayerNotifier();
});

/// Audio player state
class AudioPlayerState {
  final bool isPlaying;
  final bool isLoading;
  final String? error;
  final Duration? duration;
  final Duration? position;

  AudioPlayerState({
    this.isPlaying = false,
    this.isLoading = false,
    this.error,
    this.duration,
    this.position,
  });

  AudioPlayerState copyWith({
    bool? isPlaying,
    bool? isLoading,
    String? error,
    Duration? duration,
    Duration? position,
  }) {
    return AudioPlayerState(
      isPlaying: isPlaying ?? this.isPlaying,
      isLoading: isLoading ?? this.isLoading,
      error: error ?? this.error,
      duration: duration ?? this.duration,
      position: position ?? this.position,
    );
  }
}

/// Audio player notifier
class AudioPlayerNotifier extends StateNotifier<AudioPlayerState> {
  final AudioPlayer _player = AudioPlayer();

  AudioPlayerNotifier() : super(AudioPlayerState()) {
    _player.playerStateStream.listen((playerState) {
      state = state.copyWith(
        isPlaying: playerState.playing,
        isLoading: playerState.processingState == ProcessingState.loading,
      );
    });

    _player.durationStream.listen((duration) {
      state = state.copyWith(duration: duration);
    });

    _player.positionStream.listen((position) {
      state = state.copyWith(position: position);
    });
  }

  /// Load and play audio from URL
  Future<void> play(String audioUrl) async {
    try {
      state = state.copyWith(isLoading: true, error: null);
      await _player.setUrl(audioUrl);
      await _player.play();
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: 'Failed to play audio: $e',
      );
    }
  }

  /// Pause playback
  Future<void> pause() async {
    await _player.pause();
  }

  /// Stop playback
  Future<void> stop() async {
    await _player.stop();
  }

  /// Dispose
  @override
  void dispose() {
    _player.dispose();
    super.dispose();
  }
}

/// Audio player widget
class AudioPlayerWidget extends ConsumerWidget {
  final String? audioUrl;
  final VoidCallback? onGenerateAudio;

  const AudioPlayerWidget({
    super.key,
    this.audioUrl,
    this.onGenerateAudio,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final playerState = ref.watch(audioPlayerProvider);
    final playerNotifier = ref.read(audioPlayerProvider.notifier);

    // If no audio URL, show generate button
    if (audioUrl == null || audioUrl!.isEmpty) {
      return ElevatedButton.icon(
        onPressed: onGenerateAudio,
        icon: const Icon(Icons.play_arrow),
        label: const Text('Generate Audio'),
      );
    }

    // Show player controls
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            IconButton(
              icon: Icon(playerState.isPlaying ? Icons.pause : Icons.play_arrow),
              onPressed: () {
                if (playerState.isPlaying) {
                  playerNotifier.pause();
                } else {
                  playerNotifier.play(audioUrl!);
                }
              },
            ),
            IconButton(
              icon: const Icon(Icons.stop),
              onPressed: () => playerNotifier.stop(),
            ),
            if (playerState.isLoading)
              const Padding(
                padding: EdgeInsets.all(8.0),
                child: SizedBox(
                  width: 16,
                  height: 16,
                  child: CircularProgressIndicator(strokeWidth: 2),
                ),
              ),
          ],
        ),
        if (playerState.error != null)
          Padding(
            padding: const EdgeInsets.all(8.0),
            child: Text(
              playerState.error!,
              style: TextStyle(color: Colors.red[700], fontSize: 12),
            ),
          ),
      ],
    );
  }
}
