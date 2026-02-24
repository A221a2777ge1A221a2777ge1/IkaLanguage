import 'package:flutter/material.dart';
import 'screens/splash_screen.dart';

/// Main app widget – light theme so nav bar and text are always visible
class IkaApp extends StatelessWidget {
  const IkaApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'IKA Language Engine',
      theme: ThemeData(
        useMaterial3: true,
        colorScheme: ColorScheme.fromSeed(
          seedColor: Colors.blue,
          brightness: Brightness.light,
          primary: Colors.blue.shade700,
          onPrimary: Colors.white,
          surface: Colors.white,
          onSurface: Colors.black87,
        ),
        appBarTheme: const AppBarTheme(
          foregroundColor: Colors.black87,
          backgroundColor: Colors.white,
          elevation: 0,
        ),
        bottomNavigationBarTheme: const BottomNavigationBarThemeData(
          backgroundColor: Colors.white,
          selectedItemColor: Colors.blue,
          unselectedItemColor: Colors.black54,
          type: BottomNavigationBarType.fixed,
        ),
      ),
      home: const SplashScreen(),
      debugShowCheckedModeBanner: false,
    );
  }
}
