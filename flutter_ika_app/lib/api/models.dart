/// API Models for IKA Language Engine
library;

/// Translate request model
class TranslateRequest {
  final String text;
  final String tense; // present|past|future|progressive
  final String mode; // auto|en_to_ika|ika_to_en|rule_based

  TranslateRequest({
    required this.text,
    this.tense = 'present',
    this.mode = 'auto',
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

/// Generate (story) request model — matches backend StoryIn
class GenerateRequest {
  final String prompt;
  final String length; // short|medium|long

  GenerateRequest({
    required this.prompt,
    this.length = 'short',
  });

  Map<String, dynamic> toJson() => {
        'prompt': prompt,
        'length': length,
      };
}

/// Generate response model
class GenerateResponse {
  final String text;
  final Map<String, dynamic> meta;

  GenerateResponse({
    required this.text,
    this.meta = const {},
  });

  factory GenerateResponse.fromJson(Map<String, dynamic> json) =>
      GenerateResponse(
        text: json['text'] ?? '',
        meta: json['meta'] ?? {},
      );

  String? get englishBacktranslation =>
      meta['english_backtranslation'] as String?;
  List<String>? get notes =>
      (meta['notes'] as List<dynamic>?)?.cast<String>();
}

/// Naturalize request — "Say it like an Ika person"
class NaturalizeRequest {
  final String intentText;
  final String tone;
  final String length;

  NaturalizeRequest({
    required this.intentText,
    this.tone = 'polite',
    this.length = 'short',
  });

  Map<String, dynamic> toJson() => {
        'intent_text': intentText,
        'tone': tone,
        'length': length,
      };
}

/// Naturalize response
class NaturalizeResponse {
  final String ika;
  final String englishBacktranslation;
  final List<String> notes;

  NaturalizeResponse({
    required this.ika,
    required this.englishBacktranslation,
    this.notes = const [],
  });

  factory NaturalizeResponse.fromJson(Map<String, dynamic> json) =>
      NaturalizeResponse(
        ika: json['ika'] ?? '',
        englishBacktranslation: json['english_backtranslation'] ?? '',
        notes: (json['notes'] as List<dynamic>?)?.map((e) => e.toString()).toList() ?? [],
      );
}

/// Generate audio request model
class GenerateAudioRequest {
  final String text;
  final String voice;
  final String speed;
  final String format;

  GenerateAudioRequest({
    required this.text,
    this.voice = 'default',
    this.speed = '1.0',
    this.format = 'mp3',
  });

  Map<String, dynamic> toJson() => {
        'text': text,
        'voice': voice,
        'speed': speed,
        'format': format,
      };
}

/// Generate audio response model
class GenerateAudioResponse {
  final bool cacheHit;
  final String audioUrl;
  final String filename;
  final String text;

  GenerateAudioResponse({
    required this.audioUrl,
    this.cacheHit = false,
    this.filename = '',
    this.text = '',
  });

  factory GenerateAudioResponse.fromJson(Map<String, dynamic> json) =>
      GenerateAudioResponse(
        cacheHit: json['cache_hit'] ?? false,
        audioUrl: json['audio_url'] ?? '',
        filename: json['filename'] ?? '',
        text: json['text'] ?? '',
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
