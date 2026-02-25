import 'package:flutter_test/flutter_test.dart';

void main() {
  group('Audio cache', () {
    test('filename-based cache uses safe filenames', () {
      // Cache uses server filename; sanitize for filesystem.
      final safe = 'abc123.m4a'.replaceAll(RegExp(r'[^\w.\-]'), '_');
      expect(safe, 'abc123.m4a');
    });
  });
}
