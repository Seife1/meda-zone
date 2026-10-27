import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../features/auth/auth_provider.dart';
import '../features/splash/splash_screen.dart';
import '../features/auth/login_screen.dart';
import '../features/auth/register_screen.dart';
import '../features/map/map_screen.dart';
import '../features/field/field_detail_screen.dart';
import '../features/booking/booking_confirm_screen.dart';
import '../features/booking/bookings_list_screen.dart';
import '../features/booking/booking_detail_screen.dart';
import '../features/subscription/subscription_detail_screen.dart';
import '../features/subscription/subscription_management_screen.dart';
import '../features/payment/payment_screen.dart';
import '../features/notifications/notification_settings_screen.dart';
import '../features/profile/profile_screen.dart';
import '../shared/widgets/app_shell.dart';

// ── Simple 404-style error page ───────────────────────────────────────────────
class _NotFoundScreen extends StatelessWidget {
  final String message;
  const _NotFoundScreen({this.message = 'Page not found.'});

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: const Text('Error')),
        body: Center(
          child: Padding(
            padding: const EdgeInsets.all(32),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Text('⚠️', style: TextStyle(fontSize: 48)),
                const SizedBox(height: 16),
                Text(
                  message,
                  textAlign: TextAlign.center,
                  style: const TextStyle(fontSize: 16),
                ),
                const SizedBox(height: 24),
                ElevatedButton(
                  onPressed: () => context.go('/map'),
                  child: const Text('Back to Map'),
                ),
              ],
            ),
          ),
        ),
      );
}

// ── Route definitions ─────────────────────────────────────────────────────────
// Routes:
//   /splash                   → SplashScreen
//   /login                    → LoginScreen
//   /register                 → RegisterScreen
//   Shell (bottom nav):
//     /map                    → MapScreen (home after auth)
//     /bookings               → BookingsListScreen
//     /profile                → ProfileScreen
//   /fields/:id               → FieldDetailScreen  (no bottom nav)
//   /fields/:id/book/:slot_id → BookingConfirmScreen
//   /bookings/:id             → BookingDetailScreen
//   /subscriptions/:id        → SubscriptionDetailScreen
//   /subscriptions/manage     → SubscriptionManagementScreen
//   /payment/:sub_id          → PaymentScreen
//   /notifications/settings   → NotificationSettingsScreen

final routerProvider = Provider<GoRouter>((ref) {
  final authState = ref.watch(authProvider);

  return GoRouter(
    initialLocation: '/splash',
    refreshListenable: _AuthChangeNotifier(ref),
    redirect: (context, state) {
      // During initial load, let the splash handle it.
      if (authState.isLoading) return null;

      final isAuth = authState.isAuthenticated;
      final loc = state.matchedLocation;

      // Auth-only routes
      const authRoutes = ['/login', '/register', '/splash'];
      final isAuthRoute = authRoutes.contains(loc);

      // Unauthenticated and not on an auth route → send to login
      if (!isAuth && !isAuthRoute) return '/login';

      // Authenticated and on login/register → send to map
      if (isAuth && (loc == '/login' || loc == '/register')) {
        return '/map';
      }

      return null;
    },
    routes: [
      GoRoute(
        path: '/splash',
        builder: (_, __) => const SplashScreen(),
      ),
      GoRoute(
        path: '/login',
        builder: (_, __) => const LoginScreen(),
      ),
      GoRoute(
        path: '/register',
        builder: (_, __) => const RegisterScreen(),
      ),

      // ── Shell: main tabs with bottom navigation bar ──────────────────────
      ShellRoute(
        builder: (context, state, child) => AppShell(child: child),
        routes: [
          GoRoute(
            path: '/map',
            builder: (_, __) => const MapScreen(),
          ),
          GoRoute(
            path: '/bookings',
            builder: (_, __) => const BookingsListScreen(),
          ),
          GoRoute(
            path: '/profile',
            builder: (_, __) => const ProfileScreen(),
          ),
        ],
      ),

      // ── Field routes (no bottom nav — detail / booking flow) ─────────────
      GoRoute(
        path: '/fields/:id',
        builder: (_, state) {
          final fieldId = state.pathParameters['id'] ?? '';
          return FieldDetailScreen(fieldId: fieldId);
        },
        routes: [
          GoRoute(
            path: 'book/:slot_id',
            builder: (_, state) {
              final fieldId = state.pathParameters['id'] ?? '';
              final slotId = state.pathParameters['slot_id'] ?? '';
              return BookingConfirmScreen(fieldId: fieldId, slotId: slotId);
            },
          ),
        ],
      ),

      // ── Booking detail (no bottom nav) ───────────────────────────────────
      GoRoute(
        path: '/bookings/:id',
        builder: (_, state) {
          final bookingId = state.pathParameters['id'] ?? '';
          return BookingDetailScreen(bookingId: bookingId);
        },
      ),

      // ── Subscription routes — /manage must be before /:id ────────────────
      GoRoute(
        path: '/subscriptions/manage',
        builder: (_, __) => const SubscriptionManagementScreen(),
      ),
      GoRoute(
        path: '/subscriptions/:id',
        builder: (_, state) {
          final subId = state.pathParameters['id'] ?? '';
          return SubscriptionDetailScreen(subId: subId);
        },
      ),

      // ── Payment ──────────────────────────────────────────────────────────
      GoRoute(
        path: '/payment/:sub_id',
        builder: (_, state) {
          final subId = state.pathParameters['sub_id'] ?? '';
          return PaymentScreen(subId: subId);
        },
      ),

      // ── Notification settings ─────────────────────────────────────────────
      GoRoute(
        path: '/notifications/settings',
        builder: (_, __) => const NotificationSettingsScreen(),
      ),
    ],
    errorBuilder: (_, state) => _NotFoundScreen(
      message: state.error?.message ?? 'Page not found.',
    ),
  );
});

/// Bridges Riverpod auth state changes into the GoRouter Listenable interface
/// so the router re-evaluates its redirect whenever auth changes.
class _AuthChangeNotifier extends ChangeNotifier {
  _AuthChangeNotifier(Ref ref) {
    ref.listen(authProvider, (_, __) => notifyListeners());
  }
}
