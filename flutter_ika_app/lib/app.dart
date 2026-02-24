import 'package:flutter/material.dart';
import 'screens/splash_screen.dart';

/// Main app widget
class IkaApp extends StatelessWidget {
  const IkaApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'IKA Language Engine',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.blue),
        useMaterial3: true,
      ),
      home: const SplashScreen(),
      debugShowCheckedModeBanner: false,
    );
  }
}
