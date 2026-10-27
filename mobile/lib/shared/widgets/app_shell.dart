import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../core/theme.dart';

/// Shell scaffold that wraps all main sections with a persistent
/// bottom navigation bar (Map, Bookings, Profile).
class AppShell extends StatelessWidget {
  final Widget child;
  const AppShell({super.key, required this.child});

  static const _tabs = [
    _TabItem(icon: Icons.map_outlined,     activeIcon: Icons.map,         label: 'Map',      path: '/map'),
    _TabItem(icon: Icons.event_note_outlined, activeIcon: Icons.event_note, label: 'Bookings', path: '/bookings'),
    _TabItem(icon: Icons.person_outline,   activeIcon: Icons.person,      label: 'Profile',  path: '/profile'),
  ];

  int _currentIndex(BuildContext context) {
    final location = GoRouterState.of(context).matchedLocation;
    for (int i = 0; i < _tabs.length; i++) {
      if (location.startsWith(_tabs[i].path)) return i;
    }
    return 0;
  }

  @override
  Widget build(BuildContext context) {
    final index = _currentIndex(context);

    return Scaffold(
      body: child,
      bottomNavigationBar: BottomNavigationBar(
        currentIndex: index,
        onTap: (i) {
          if (i != index) {
            context.go(_tabs[i].path);
          }
        },
        items: _tabs.map((tab) => BottomNavigationBarItem(
          icon: Icon(tab.icon),
          activeIcon: Icon(tab.activeIcon),
          label: tab.label,
        )).toList(),
      ),
    );
  }
}

class _TabItem {
  final IconData icon;
  final IconData activeIcon;
  final String label;
  final String path;
  const _TabItem({
    required this.icon,
    required this.activeIcon,
    required this.label,
    required this.path,
  });
}
