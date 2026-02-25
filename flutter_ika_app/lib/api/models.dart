/// API Models for IKA Language Engine
library;

/// Translate request model (POST /translate)
/// mode: rule_based | en_to_ika | ika_to_en | auto
class TranslateRequest {
  final String text;
  final String tense; // present|past|future|progressive
  final String mode; // rule_based|en_to_ika|ika_to_en|auto

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
    required this.meta,
  });

  factory GenerateResponse.fromJson(Map<String, dynamic> json) =>
      GenerateResponse(
        text: json['text'] ?? '',
        meta: json['meta'] ?? {},
      );
}

/// Generate audio request model (POST /generate-audio)
class GenerateAudioRequest {
  final String text;
  final String voice;
  final double? speed;
  final String? format;

  GenerateAudioRequest({
    required this.text,
    this.voice = 'default',
    this.speed,
    this.format,
  });

  Map<String, dynamic> toJson() => {
        'text': text,
        'voice': voice,
        if (speed != null) 'speed': speed,
        if (format != null) 'format': format,
      };
}

/// Generate audio response (audio_url + filename for GET /audio/{filename})
class GenerateAudioResponse {
  final String audioUrl;
  final String filename;

  GenerateAudioResponse({
    required this.audioUrl,
    this.filename = '',
  });

  factory GenerateAudioResponse.fromJson(Map<String, dynamic> json) =>
      GenerateAudioResponse(
        audioUrl: json['audio_url'] ?? '',
        filename: json['filename'] ?? '',
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
  final String? audioUrl;

  DictionaryEntry({
    required this.sourceText,
    required this.targetText,
    this.pos,
    this.domain,
    this.docId,
    this.audioUrl,
  });

  factory DictionaryEntry.fromJson(Map<String, dynamic> json) =>
      DictionaryEntry(
        sourceText: json['source_text'] ?? json['en'] ?? '',
        targetText: json['target_text'] ?? json['ika'] ?? '',
        pos: json['pos'],
        domain: json['domain'],
        docId: json['doc_id'] ?? json['id']?.toString(),
        audioUrl: json['audio_url'],
      );
}

/// EN→Ika lookup response (GET /api/translate/en-ika)
class EnIkaLookupResponse {
  final bool found;
  final String query;
  final List<EnIkaCandidate> candidates;
  final List<Map<String, dynamic>> suggestions;

  EnIkaLookupResponse({
    required this.found,
    required this.query,
    required this.candidates,
    required this.suggestions,
  });

  factory EnIkaLookupResponse.fromJson(Map<String, dynamic> json) {
    final candList = json['candidates'];
    return EnIkaLookupResponse(
      found: json['found'] ?? false,
      query: json['query'] ?? '',
      candidates: candList is List
          ? (candList as List)
              .map((e) => EnIkaCandidate.fromJson(e as Map<String, dynamic>))
              .toList()
          : [],
      suggestions: (json['suggestions'] is List)
          ? List<Map<String, dynamic>>.from(json['suggestions'] as List)
          : [],
    );
  }
}

class EnIkaCandidate {
  final String id;
  final String ika;
  final String? domain;
  final String? audioUrl;

  EnIkaCandidate({
    required this.id,
    required this.ika,
    this.domain,
    this.audioUrl,
  });

  factory EnIkaCandidate.fromJson(Map<String, dynamic> json) =>
      EnIkaCandidate(
        id: json['id']?.toString() ?? '',
        ika: json['ika'] ?? '',
        domain: json['domain'],
        audioUrl: json['audio_url'],
      );
}

/// Ika→EN lookup response (GET /api/translate/ika-en)
class IkaEnLookupResponse {
  final bool found;
  final String query;
  final List<String> meanings;
  final List<Map<String, dynamic>>? suggestions;

  IkaEnLookupResponse({
    required this.found,
    required this.query,
    required this.meanings,
    this.suggestions,
  });

  factory IkaEnLookupResponse.fromJson(Map<String, dynamic> json) =>
      IkaEnLookupResponse(
        found: json['found'] ?? false,
        query: json['query'] ?? '',
        meanings: (json['meanings'] is List)
            ? List<String>.from(json['meanings'] as List)
            : [],
        suggestions: json['suggestions'] != null
            ? List<Map<String, dynamic>>.from(json['suggestions'] as List)
            : null,
      );
}

/// List dictionary response (GET /api/dictionary)
class DictionaryListResponse {
  final List<DictionaryEntry> entries;

  DictionaryListResponse({required this.entries});

  factory DictionaryListResponse.fromJson(Map<String, dynamic> json) {
    final list = json['entries'];
    if (list is! List) return DictionaryListResponse(entries: []);
    return DictionaryListResponse(
      entries: (list as List)
          .map((e) => DictionaryEntry.fromJson(e as Map<String, dynamic>))
          .toList(),
    );
  }
}

/// API generate response (POST /api/generate)
class ApiGenerateResponse {
  final String text;
  final Map<String, dynamic> meta;
  final List<String>? missingConcepts;

  ApiGenerateResponse({
    required this.text,
    required this.meta,
    this.missingConcepts,
  });

  factory ApiGenerateResponse.fromJson(Map<String, dynamic> json) =>
      ApiGenerateResponse(
        text: json['text'] ?? '',
        meta: json['meta'] ?? {},
        missingConcepts: json['missing_concepts'] != null
            ? List<String>.from(json['missing_concepts'] as List)
            : null,
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
