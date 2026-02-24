import 'package:flutter/material.dart';
import 'translate_screen.dart';
import 'generate_screen.dart';
import 'dictionary_screen.dart';
import 'library_screen.dart';
import 'settings_screen.dart';

/// Home screen with bottom navigation
class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  int _currentIndex = 0;

  final List<Widget> _screens = [
    const TranslateScreen(),
    const GenerateScreen(),
    const DictionaryScreen(),
    const LibraryScreen(),
    const SettingsScreen(),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      extendBody: false,
      appBar: AppBar(
        title: const Text('IKA Language Engine'),
        elevation: 0,
      ),
      body: SafeArea(
        child: IndexedStack(
          index: _currentIndex,
          children: _screens,
        ),
      ),
      bottomNavigationBar: Container(
        decoration: BoxDecoration(
          color: Colors.white,
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.12),
              blurRadius: 8,
              offset: const Offset(0, -2),
            ),
          ],
        ),
        child: SafeArea(
          child: BottomNavigationBar(
            currentIndex: _currentIndex,
            onTap: (index) {
              setState(() {
                _currentIndex = index;
              });
            },
            backgroundColor: Colors.white,
            selectedItemColor: Colors.blue.shade700,
            unselectedItemColor: Colors.black54,
            type: BottomNavigationBarType.fixed,
            items: const [
            BottomNavigationBarItem(
              icon: Icon(Icons.translate),
              label: 'Translate',
            ),
            BottomNavigationBarItem(
              icon: Icon(Icons.auto_stories),
              label: 'Generate',
            ),
            BottomNavigationBarItem(
              icon: Icon(Icons.menu_book),
              label: 'Dictionary',
            ),
            BottomNavigationBarItem(
              icon: Icon(Icons.library_books),
              label: 'Library',
            ),
            BottomNavigationBarItem(
              icon: Icon(Icons.settings),
              label: 'Settings',
            ),
          ],
          ),
        ),
      ),
    );
  }
}
