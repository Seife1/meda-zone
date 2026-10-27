import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'core/fcm_handler.dart';
import 'core/router.dart';
import 'core/theme.dart';

// ── Background message handler (top-level, required by firebase_messaging) ────
// Runs in a separate isolate — keep it minimal.
@pragma('vm:entry-point')
Future<void> _firebaseMessagingBackgroundHandler(RemoteMessage message) async {
  await Firebase.initializeApp();
  // The OS auto-displays FCM notifications that include a "notification" block.
  // Do not call showLocalNotification here to avoid duplicates.
}

// ── GoRouter reference for FCM tap navigation ─────────────────────────────────
GoRouter? _router;

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // 1. Initialize Firebase (used for FCM only — no Firebase Auth)
  await Firebase.initializeApp();

  // 2. FCM setup — skip on Web (service worker not available in dev)
  if (!kIsWeb) {
    FirebaseMessaging.onBackgroundMessage(_firebaseMessagingBackgroundHandler);

    await initFcm(
      onTap: (route) {
        try {
          _router?.go(route);
        } catch (_) {
          // Router not ready yet — GoRouter will handle the initial location.
        }
      },
    );
  }

  runApp(const ProviderScope(child: MedaZoneApp()));
}

class MedaZoneApp extends ConsumerWidget {
  const MedaZoneApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final router = ref.watch(routerProvider);
    // Store reference so FCM notification taps can navigate.
    _router = router;

    return MaterialApp.router(
      title: 'MedaZone',
      debugShowCheckedModeBanner: false,
      // Req 18.6: light and dark themes, following device system setting
      theme: AppTheme.light,
      darkTheme: AppTheme.dark,
      themeMode: ThemeMode.system,
      routerConfig: router,
    );
  }
}
