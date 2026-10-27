import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/api_client.dart';
import '../../core/theme.dart';

// ── Provider ──────────────────────────────────────────────────────────────────

class _NotifPrefs {
  final bool bookingConfirmed;
  final bool bookingReminder;
  final bool bookingCancelled;
  final bool slotAvailable;
  final bool subscriptionExpiry;

  const _NotifPrefs({
    this.bookingConfirmed = true,
    this.bookingReminder = true,
    this.bookingCancelled = true,
    this.slotAvailable = true,
    this.subscriptionExpiry = true,
  });

  factory _NotifPrefs.fromJson(Map<String, dynamic> j) => _NotifPrefs(
        bookingConfirmed: j['booking_confirmed'] as bool? ?? true,
        bookingReminder: j['booking_reminder'] as bool? ?? true,
        bookingCancelled: j['booking_cancelled'] as bool? ?? true,
        slotAvailable: j['slot_available'] as bool? ?? true,
        subscriptionExpiry: j['subscription_expiry'] as bool? ?? true,
      );

  Map<String, dynamic> toJson() => {
        'booking_confirmed': bookingConfirmed,
        'booking_reminder': bookingReminder,
        'booking_cancelled': bookingCancelled,
        'slot_available': slotAvailable,
        'subscription_expiry': subscriptionExpiry,
      };

  _NotifPrefs copyWith({
    bool? bookingConfirmed, bool? bookingReminder, bool? bookingCancelled,
    bool? slotAvailable, bool? subscriptionExpiry,
  }) => _NotifPrefs(
        bookingConfirmed: bookingConfirmed ?? this.bookingConfirmed,
        bookingReminder: bookingReminder ?? this.bookingReminder,
        bookingCancelled: bookingCancelled ?? this.bookingCancelled,
        slotAvailable: slotAvailable ?? this.slotAvailable,
        subscriptionExpiry: subscriptionExpiry ?? this.subscriptionExpiry,
      );
}

class _PrefsNotifier extends StateNotifier<AsyncValue<_NotifPrefs>> {
  _PrefsNotifier() : super(const AsyncLoading()) { _load(); }

  Future<void> _load() async {
    try {
      final resp = await ApiClient.dio.get('/notifications/preferences');
      state = AsyncData(_NotifPrefs.fromJson(resp.data as Map<String, dynamic>));
    } catch (e) {
      state = AsyncData(const _NotifPrefs()); // fallback to defaults
    }
  }

  Future<void> update(_NotifPrefs prefs) async {
    state = AsyncData(prefs);
    try {
      await ApiClient.dio.put('/notifications/preferences', data: prefs.toJson());
    } catch (_) {}
  }
}

final _prefsNotifierProvider =
    StateNotifierProvider<_PrefsNotifier, AsyncValue<_NotifPrefs>>(
  (_) => _PrefsNotifier(),
);

// ── Screen ────────────────────────────────────────────────────────────────────

class NotificationSettingsScreen extends ConsumerWidget {
  const NotificationSettingsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final prefsAsync = ref.watch(_prefsNotifierProvider);

    return Scaffold(
      appBar: const BrandAppBar(),
      body: prefsAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text('$e')),
        data: (prefs) => ListView(
          padding: const EdgeInsets.all(20),
          children: [
            Text('Notifications', style: Theme.of(context).textTheme.headlineMedium),
            const SizedBox(height: 6),
            Text('Manage what you want to be notified about.',
                style: Theme.of(context).textTheme.bodySmall),
            const SizedBox(height: 24),
            _Toggle(
              icon: Icons.check_circle_outline,
              title: 'Booking Confirmed',
              subtitle: 'When your booking is confirmed',
              value: prefs.bookingConfirmed,
              onChanged: (v) => ref.read(_prefsNotifierProvider.notifier)
                  .update(prefs.copyWith(bookingConfirmed: v)),
            ),
            _Toggle(
              icon: Icons.alarm,
              title: 'Booking Reminder',
              subtitle: '1 hour before your session starts',
              value: prefs.bookingReminder,
              onChanged: (v) => ref.read(_prefsNotifierProvider.notifier)
                  .update(prefs.copyWith(bookingReminder: v)),
            ),
            _Toggle(
              icon: Icons.cancel_outlined,
              title: 'Booking Cancelled',
              subtitle: 'When a booking is cancelled',
              value: prefs.bookingCancelled,
              onChanged: (v) => ref.read(_prefsNotifierProvider.notifier)
                  .update(prefs.copyWith(bookingCancelled: v)),
            ),
            _Toggle(
              icon: Icons.sports_soccer,
              title: 'Slot Available',
              subtitle: 'When a slot opens at a watched field',
              value: prefs.slotAvailable,
              onChanged: (v) => ref.read(_prefsNotifierProvider.notifier)
                  .update(prefs.copyWith(slotAvailable: v)),
            ),
            _Toggle(
              icon: Icons.card_membership,
              title: 'Subscription Expiry',
              subtitle: '3 days before your subscription expires',
              value: prefs.subscriptionExpiry,
              onChanged: (v) => ref.read(_prefsNotifierProvider.notifier)
                  .update(prefs.copyWith(subscriptionExpiry: v)),
            ),
          ],
        ),
      ),
    );
  }
}

class _Toggle extends StatelessWidget {
  final IconData icon;
  final String title;
  final String subtitle;
  final bool value;
  final ValueChanged<bool> onChanged;

  const _Toggle({
    required this.icon, required this.title, required this.subtitle,
    required this.value, required this.onChanged,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      decoration: BoxDecoration(
        border: Border.all(
          color: value ? AppColors.primaryGreen.withOpacity(0.4) : Colors.grey.shade200),
        borderRadius: BorderRadius.circular(14),
      ),
      child: SwitchListTile(
        secondary: Icon(icon, color: value ? AppColors.primaryGreen : Colors.grey),
        title: Text(title, style: TextStyle(
            fontWeight: FontWeight.w600,
            color: value ? AppColors.darkNavy : Colors.grey)),
        subtitle: Text(subtitle, style: const TextStyle(fontSize: 12)),
        value: value,
        onChanged: onChanged,
        activeColor: AppColors.primaryGreen,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
      ),
    );
  }
}
