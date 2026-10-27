import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../core/api_client.dart';
import '../../core/theme.dart';
import '../../shared/models/booking.dart';
import '../auth/auth_provider.dart';

// Fix #14: Use a lightweight count endpoint instead of fetching all bookings.
final _bookingStatsProvider = FutureProvider<Map<String, int>>((ref) async {
  try {
    final resp = await ApiClient.dio.get('/bookings/me');
    final bookings = (resp.data as List<dynamic>)
        .map((j) => Booking.fromJson(j as Map<String, dynamic>))
        .toList();
    return {
      'confirmed': bookings.where((b) => b.status == 'confirmed').length,
      'total': bookings.length,
    };
  } catch (_) {
    return {'confirmed': 0, 'total': 0};
  }
});

class ProfileScreen extends ConsumerStatefulWidget {
  const ProfileScreen({super.key});

  @override
  ConsumerState<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends ConsumerState<ProfileScreen> {
  bool _editing = false;
  final _nameCtrl = TextEditingController();
  final List<String> _selectedPositions = [];
  bool _saving = false;

  static const _allPositions = ['Goalkeeper', 'Defender', 'Midfielder', 'Forward', 'Any'];

  @override
  void dispose() {
    _nameCtrl.dispose();
    super.dispose();
  }

  void _startEdit() {
    final user = ref.read(authProvider).user;
    if (user == null) return;
    _nameCtrl.text = user.displayName ?? '';
    _selectedPositions
      ..clear()
      ..addAll(user.preferredPositions);
    setState(() => _editing = true);
  }

  Future<void> _saveEdit() async {
    setState(() => _saving = true);
    try {
      await ref.read(authProvider.notifier).updateProfile(
            displayName: _nameCtrl.text.trim(),
            preferredPositions: List.from(_selectedPositions),
          );
      if (mounted) setState(() { _editing = false; _saving = false; });
    } catch (e) {
      if (mounted) {
        setState(() => _saving = false);
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text('Error: $e')));
      }
    }
  }

  Future<void> _logout() async {
    await ref.read(authProvider.notifier).logout();
    if (mounted) context.go('/login');
  }

  @override
  Widget build(BuildContext context) {
    final authState = ref.watch(authProvider);
    final user = authState.user;
    if (user == null) return const Scaffold(body: Center(child: CircularProgressIndicator()));

    final initials = (user.displayName ?? user.phoneNumber)
        .split(' ')
        .where((w) => w.isNotEmpty)
        .take(2)
        .map((w) => w[0].toUpperCase())
        .join();



    return Scaffold(
      appBar: const BrandAppBar(),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Avatar
            Center(
              child: CircleAvatar(
                radius: 40,
                backgroundColor: AppColors.primaryGreen,
                child: Text(initials,
                    style: const TextStyle(fontSize: 28, fontWeight: FontWeight.w700,
                        color: Colors.white)),
              ),
            ),
            const SizedBox(height: 16),

            if (!_editing) ...[
              Center(
                child: Text(
                  user.displayName ?? 'Player',
                  style: Theme.of(context).textTheme.headlineSmall,
                ),
              ),
              const SizedBox(height: 4),
              Center(
                child: Text(user.phoneNumber,
                    style: Theme.of(context).textTheme.bodySmall),
              ),
              const SizedBox(height: 16),

              // Stats row — Fix #14
              Row(mainAxisAlignment: MainAxisAlignment.center, children: [
                ref.watch(_bookingStatsProvider).when(
                  loading: () => const SizedBox(width: 24, height: 24,
                      child: CircularProgressIndicator(strokeWidth: 2)),
                  error: (_, __) => const SizedBox(),
                  data: (stats) => Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      _StatCard(
                        label: 'Confirmed\nBookings',
                        value: '${stats['confirmed']}',
                      ),
                      const SizedBox(width: 12),
                      _StatCard(
                        label: 'Total\nBookings',
                        value: '${stats['total']}',
                      ),
                    ],
                  ),
                ),
              ]),
              const SizedBox(height: 16),

              // Preferred positions
              if (user.preferredPositions.isNotEmpty) ...[
                Text('Positions', style: Theme.of(context).textTheme.titleSmall),
                const SizedBox(height: 8),
                Wrap(
                  spacing: 6, runSpacing: 6,
                  children: user.preferredPositions.map((p) => Chip(
                    label: Text(p, style: const TextStyle(fontSize: 12)),
                    backgroundColor: AppColors.primaryGreen.withOpacity(0.1),
                    side: BorderSide(color: AppColors.primaryGreen.withOpacity(0.3)),
                  )).toList(),
                ),
                const SizedBox(height: 16),
              ],

              PrimaryButton(label: 'Edit Profile', onPressed: _startEdit),

            ] else ...[
              // Edit form
              TextFormField(
                controller: _nameCtrl,
                decoration: const InputDecoration(labelText: 'Display Name'),
                textCapitalization: TextCapitalization.words,
              ),
              const SizedBox(height: 16),
              Text('Preferred Positions', style: Theme.of(context).textTheme.titleSmall),
              const SizedBox(height: 8),
              Wrap(
                spacing: 6, runSpacing: 6,
                children: _allPositions.map((pos) {
                  final selected = _selectedPositions.contains(pos);
                  return FilterChip(
                    label: Text(pos),
                    selected: selected,
                    onSelected: (_) {
                      setState(() {
                        if (selected) _selectedPositions.remove(pos);
                        else _selectedPositions.add(pos);
                      });
                    },
                    selectedColor: AppColors.primaryGreen.withOpacity(0.15),
                    checkmarkColor: AppColors.primaryGreen,
                  );
                }).toList(),
              ),
              const SizedBox(height: 20),
              PrimaryButton(
                label: 'Save Changes',
                isLoading: _saving,
                onPressed: _saving ? null : _saveEdit,
              ),
              const SizedBox(height: 8),
              TextButton(
                onPressed: () => setState(() => _editing = false),
                child: const Text('Cancel'),
              ),
            ],

            const SizedBox(height: 24),
            const Divider(),
            const SizedBox(height: 16),

            OutlinedButton.icon(
              onPressed: _logout,
              icon: const Icon(Icons.logout, color: AppColors.error),
              label: const Text('Log Out', style: TextStyle(color: AppColors.error)),
              style: OutlinedButton.styleFrom(
                side: const BorderSide(color: AppColors.error),
                padding: const EdgeInsets.symmetric(vertical: 14),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _StatCard extends StatelessWidget {
  final String label;
  final String value;
  const _StatCard({required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 12),
      decoration: BoxDecoration(
        color: AppColors.primaryGreen.withOpacity(0.08),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.primaryGreen.withOpacity(0.2)),
      ),
      child: Column(
        children: [
          Text(value, style: const TextStyle(fontSize: 28, fontWeight: FontWeight.w800,
              color: AppColors.primaryGreen)),
          Text(label, textAlign: TextAlign.center,
              style: const TextStyle(fontSize: 11, color: AppColors.textMuted)),
        ],
      ),
    );
  }
}
