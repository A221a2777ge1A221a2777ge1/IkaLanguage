/// API Models for IKA Language Engine
library;

/// Translate request model
class TranslateRequest {
  final String text;
  final String tense; // present|past|future|progressive
  final String mode; // rule_based

  TranslateRequest({
    required this.text,
    this.tense = 'present',
    this.mode = 'rule_based',
  });

  Map<String, dynamic> toJson() => {
        'text': text,
        'tense': tense,
        'mode': mode,
      };
}

/// Translate response model
class TranslateResponse {
  final String text;
  final Map<String, dynamic> meta;

  TranslateResponse({
    required this.text,
    required this.meta,
  });

  factory TranslateResponse.fromJson(Map<String, dynamic> json) =>
      TranslateResponse(
        text: json['text'] ?? '',
        meta: json['meta'] ?? {},
      );
}

/// Generate request model
class GenerateRequest {
  final String kind; // poem|story|lecture
  final String topic;
  final String tone; // neutral|formal|poetic
  final String length; // short|medium|long

  GenerateRequest({
    required this.kind,
    required this.topic,
    this.tone = 'neutral',
    this.length = 'medium',
  });

  Map<String, dynamic> toJson() => {
        'kind': kind,
        'topic': topic,
        'tone': tone,
        'length': length,
      };
}

/// Generate response model
class GenerateResponse {
  final String text;
  final Map<String, dynamic> meta;

  GenerateResponse({
    required this.text,
    required this.meta,
  });

  factory GenerateResponse.fromJson(Map<String, dynamic> json) =>
      GenerateResponse(
        text: json['text'] ?? '',
        meta: json['meta'] ?? {},
      );
}

/// Generate audio request model
class GenerateAudioRequest {
  final String text;
  final String voice; // default

  GenerateAudioRequest({
    required this.text,
    this.voice = 'default',
  });

  Map<String, dynamic> toJson() => {
        'text': text,
        'voice': voice,
      };
}

/// Generate audio response model
class GenerateAudioResponse {
  final String audioUrl;

  GenerateAudioResponse({
    required this.audioUrl,
  });

  factory GenerateAudioResponse.fromJson(Map<String, dynamic> json) =>
      GenerateAudioResponse(
        audioUrl: json['audio_url'] ?? '',
      );
}

/// Health check response
class HealthResponse {
  final bool ok;

  HealthResponse({required this.ok});

  factory HealthResponse.fromJson(Map<String, dynamic> json) =>
      HealthResponse(ok: json['ok'] ?? false);
}

/// Dictionary entry (English → Ika)
class DictionaryEntry {
  final String sourceText;
  final String targetText;
  final String? pos;
  final String? domain;
  final String? docId;

  DictionaryEntry({
    required this.sourceText,
    required this.targetText,
    this.pos,
    this.domain,
    this.docId,
  });

  factory DictionaryEntry.fromJson(Map<String, dynamic> json) =>
      DictionaryEntry(
        sourceText: json['source_text'] ?? '',
        targetText: json['target_text'] ?? '',
        pos: json['pos'],
        domain: json['domain'],
        docId: json['doc_id'],
      );
}

/// Dictionary lookup response
class DictionaryResponse {
  final List<DictionaryEntry> entries;

  DictionaryResponse({required this.entries});

  factory DictionaryResponse.fromJson(Map<String, dynamic> json) {
    final list = json['entries'];
    if (list is! List) return DictionaryResponse(entries: []);
    return DictionaryResponse(
      entries: (list as List)
          .map((e) => DictionaryEntry.fromJson(e as Map<String, dynamic>))
          .toList(),
    );
  }
}

/// Generation result model for local storage
class GenerationResult {
  final String id;
  final String type; // translate|poem|story|lecture
  final String input; // original input text/topic
  final String outputText;
  final Map<String, dynamic> meta;
  final DateTime createdAt;
  String? audioUrl;

  GenerationResult({
    required this.id,
    required this.type,
    required this.input,
    required this.outputText,
    required this.meta,
    required this.createdAt,
    this.audioUrl,
  });

  Map<String, dynamic> toJson() => {
        'id': id,
        'type': type,
        'input': input,
        'outputText': outputText,
        'meta': meta,
        'createdAt': createdAt.toIso8601String(),
        'audioUrl': audioUrl,
      };

  factory GenerationResult.fromJson(Map<String, dynamic> json) =>
      GenerationResult(
        id: json['id'] ?? '',
        type: json['type'] ?? '',
        input: json['input'] ?? '',
        outputText: json['outputText'] ?? '',
        meta: json['meta'] ?? {},
        createdAt: DateTime.parse(json['createdAt'] ?? DateTime.now().toIso8601String()),
        audioUrl: json['audioUrl'],
      );
}
