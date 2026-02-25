import 'package:flutter/material.dart';
import 'translate_screen.dart';
import 'generate_screen.dart';
import 'dictionary_screen.dart';
import 'library_screen.dart';

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
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('IKA Language Engine'),
        elevation: 0,
      ),
      body: SafeArea(
        child: _screens[_currentIndex],
      ),
      bottomNavigationBar: SafeArea(
        child: BottomNavigationBar(
        currentIndex: _currentIndex,
        onTap: (index) {
          setState(() {
            _currentIndex = index;
          });
        },
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
        ],
      ),
      ),
    );
  }
}
