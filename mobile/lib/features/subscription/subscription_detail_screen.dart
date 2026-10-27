import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../core/api_client.dart';
import '../../core/theme.dart';
import '../../shared/models/subscription.dart';

final _subDetailProvider =
    FutureProvider.family<Subscription, String>((ref, subId) async {
  final resp = await ApiClient.dio.get('/subscriptions/$subId');
  return Subscription.fromJson(resp.data as Map<String, dynamic>);
});

class SubscriptionDetailScreen extends ConsumerWidget {
  final String subId;
  const SubscriptionDetailScreen({super.key, required this.subId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final subAsync = ref.watch(_subDetailProvider(subId));

    return Scaffold(
      appBar: const BrandAppBar(),
      body: subAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text('Error: $e')),
        data: (sub) => SingleChildScrollView(
          padding: const EdgeInsets.all(20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              _StatusBadge(sub.status),
              const SizedBox(height: 20),
              _InfoRow('Tier', sub.tier.replaceAll('_', ' ')),
              _InfoRow('Days', sub.recurringDays.join(', ')),
              _InfoRow('Time', sub.sessionStartTime),
              _InfoRow('Duration', '${sub.sessionDurationHours}h'),
              _InfoRow('Total Sessions', '${sub.totalSessions}'),
              _InfoRow('Total Price', 'ETB ${sub.totalPrice.toStringAsFixed(2)}'),
              if (sub.startDate != null) _InfoRow('Start', sub.startDate!),
              if (sub.expiryDate != null) _InfoRow('Expires', sub.expiryDate!),
              if (sub.daysRemaining != null)
                _InfoRow('Days Remaining', '${sub.daysRemaining}'),
              const SizedBox(height: 32),
              if (sub.status == 'pending_payment')
                PrimaryButton(
                  label: 'Pay ETB ${sub.totalPrice.toStringAsFixed(0)}',
                  onPressed: () => context.go('/payment/$subId'),
                ),
            ],
          ),
        ),
      ),
    );
  }
}

class _StatusBadge extends StatelessWidget {
  final String status;
  const _StatusBadge(this.status);
  @override
  Widget build(BuildContext context) {
    final color = status == 'active'
        ? AppColors.primaryGreen
        : status == 'pending_payment'
            ? AppColors.warning
            : AppColors.textMuted;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      decoration: BoxDecoration(
        color: color.withOpacity(0.12),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: color.withOpacity(0.4)),
      ),
      child: Text(
        status.toUpperCase().replaceAll('_', ' '),
        textAlign: TextAlign.center,
        style: TextStyle(color: color, fontWeight: FontWeight.w700, fontSize: 13),
      ),
    );
  }
}

class _InfoRow extends StatelessWidget {
  final String label;
  final String value;
  const _InfoRow(this.label, this.value);
  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 7),
        child: Row(
          children: [
            SizedBox(
              width: 110,
              child: Text(label,
                  style: Theme.of(context)
                      .textTheme
                      .bodySmall
                      ?.copyWith(color: AppColors.textMuted)),
            ),
            Expanded(
              child: Text(value,
                  style: const TextStyle(fontWeight: FontWeight.w600)),
            ),
          ],
        ),
      );
}
