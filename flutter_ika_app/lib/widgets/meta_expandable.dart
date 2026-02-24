import 'package:flutter/material.dart';

/// Expandable metadata widget
class MetaExpandable extends StatefulWidget {
  final Map<String, dynamic> meta;

  const MetaExpandable({
    super.key,
    required this.meta,
  });

  @override
  State<MetaExpandable> createState() => _MetaExpandableState();
}

class _MetaExpandableState extends State<MetaExpandable> {
  bool _expanded = false;

  @override
  Widget build(BuildContext context) {
    if (widget.meta.isEmpty) {
      return const SizedBox.shrink();
    }

    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: ExpansionTile(
        title: const Text('Metadata'),
        initiallyExpanded: _expanded,
        onExpansionChanged: (expanded) {
          setState(() {
            _expanded = expanded;
          });
        },
        children: [
          Padding(
            padding: const EdgeInsets.all(16.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: widget.meta.entries.map((entry) {
                return Padding(
                  padding: const EdgeInsets.only(bottom: 8.0),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      SizedBox(
                        width: 100,
                        child: Text(
                          '${entry.key}:',
                          style: const TextStyle(fontWeight: FontWeight.bold),
                        ),
                      ),
                      Expanded(
                        child: Text(
                          entry.value.toString(),
                          style: const TextStyle(fontSize: 12),
                        ),
                      ),
                    ],
                  ),
                );
              }).toList(),
            ),
          ),
        ],
      ),
    );
  }
}
