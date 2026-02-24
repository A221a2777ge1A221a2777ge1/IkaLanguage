import 'dart:io';
import 'package:flutter/material.dart';
import 'package:just_audio/just_audio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:path_provider/path_provider.dart';
import 'package:flutter/foundation.dart';
import '../services/audio_cache_service.dart';
import '../state/auth_provider.dart';

/// Audio player state provider (uses ref for authenticated download on Cloud Run)
final audioPlayerProvider = StateNotifierProvider<AudioPlayerNotifier, AudioPlayerState>((ref) {
  return AudioPlayerNotifier(ref);
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

/// Audio player notifier – uses authenticated download so /audio/xxx works on Cloud Run
class AudioPlayerNotifier extends StateNotifier<AudioPlayerState> {
  final Ref _ref;
  final AudioPlayer _player = AudioPlayer();

  AudioPlayerNotifier(this._ref) : super(AudioPlayerState()) {
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

  /// Load and play: download with auth, then play from local file. Fallback to cache if auth fails.
  Future<void> play(String audioUrl) async {
    if (audioUrl.isEmpty) return;
    try {
      state = state.copyWith(isLoading: true, error: null);
      File file;
      try {
        final api = _ref.read(ikaApiProvider);
        final bytes = await api.getAudioBytes(audioUrl);
        final dir = await getTemporaryDirectory();
        final name = audioUrl.replaceAll(RegExp(r'[^a-zA-Z0-9._-]'), '_');
        file = File('${dir.path}/ika_audio_$name');
        await file.writeAsBytes(bytes);
      } catch (e) {
        if (kDebugMode) debugPrint('Auth download failed, trying cache: $e');
        file = await AudioCacheService().getFileForUrl(audioUrl);
      }
      await _player.setFilePath(file.path);
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
  final bool cacheHit;

  const AudioPlayerWidget({
    super.key,
    this.audioUrl,
    this.onGenerateAudio,
    this.cacheHit = false,
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
            if (cacheHit)
              Padding(
                padding: const EdgeInsets.only(right: 8.0),
                child: Chip(
                  label: const Text('Cached'),
                  avatar: Icon(Icons.offline_pin, size: 18, color: Colors.green[700]),
                  materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                ),
              ),
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
