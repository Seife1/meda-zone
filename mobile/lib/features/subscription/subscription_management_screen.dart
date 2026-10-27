import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../core/api_client.dart';
import '../../core/theme.dart';
import '../../shared/models/subscription.dart';

final _mySubsProvider = FutureProvider<List<Subscription>>((ref) async {
  final resp = await ApiClient.dio.get('/subscriptions/player/me');
  return (resp.data as List<dynamic>)
      .map((j) => Subscription.fromJson(j as Map<String, dynamic>))
      .toList();
});

class SubscriptionManagementScreen extends ConsumerWidget {
  const SubscriptionManagementScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final subsAsync = ref.watch(_mySubsProvider);

    return Scaffold(
      appBar: const BrandAppBar(),
      body: subsAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => ErrorView(
          message: friendlyErrorMessage(e),
          onRetry: () => ref.refresh(_mySubsProvider),
        ),
        data: (subs) {
          if (subs.isEmpty) {
            return Center(
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 32),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Text('⚽', style: TextStyle(fontSize: 48)),
                    const SizedBox(height: 12),
                    const Text('No subscriptions yet',
                        style: TextStyle(fontWeight: FontWeight.w700, fontSize: 16)),
                    const SizedBox(height: 8),
                    const Text(
                      'Ask your field owner to create a subscription plan for you.',
                      textAlign: TextAlign.center,
                      style: TextStyle(color: AppColors.textMuted),
                    ),
                    const SizedBox(height: 20),
                    OutlinedButton.icon(
                      onPressed: () {},
                      icon: const Icon(Icons.phone_outlined,
                          color: AppColors.primaryGreen),
                      label: const Text('Call / WhatsApp Field Owner',
                          style: TextStyle(color: AppColors.primaryGreen)),
                      style: OutlinedButton.styleFrom(
                        side: const BorderSide(color: AppColors.primaryGreen),
                        shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(12)),
                      ),
                    ),
                  ],
                ),
              ),
            );
          }
          return ListView(
            padding: const EdgeInsets.all(16),
            children: subs.map((sub) => _SubscriptionCard(sub: sub, ref: ref)).toList(),
          );
        },
      ),
    );
  }
}

class _SubscriptionCard extends StatelessWidget {
  final Subscription sub;
  final WidgetRef ref;
  const _SubscriptionCard({required this.sub, required this.ref});

  @override
  Widget build(BuildContext context) {
    final isActive = sub.status == 'active';
    return Card(
      margin: const EdgeInsets.only(bottom: 16),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              children: [
                Expanded(child: Text(sub.tier.replaceAll('_', ' ').toUpperCase(),
                    style: Theme.of(context).textTheme.titleMedium)),
                _StatusDot(sub.status),
              ],
            ),
            const SizedBox(height: 8),
            Text(sub.recurringDays.join(', '),
                style: const TextStyle(fontWeight: FontWeight.w500)),
            Text('${sub.sessionStartTime} · ${sub.sessionDurationHours}h · ${sub.totalSessions} sessions'),
            if (sub.expiryDate != null) ...[
              const SizedBox(height: 4),
              Text('Expires: ${sub.expiryDate}',
                  style: TextStyle(
                    color: (sub.daysRemaining ?? 99) <= 7
                        ? AppColors.error
                        : AppColors.textMuted,
                    fontSize: 12,
                  )),
            ],
            const SizedBox(height: 12),
            if (sub.status == 'pending_payment')
              PrimaryButton(
                label: 'Pay ETB ${sub.totalPrice.toStringAsFixed(0)}',
                onPressed: () => context.go('/payment/${sub.id}'),
              ),
            if (isActive)
              OutlinedButton(
                onPressed: () => _requestRenewal(context),
                style: OutlinedButton.styleFrom(
                    side: const BorderSide(color: AppColors.primaryGreen)),
                child: const Text('Request Renewal',
                    style: TextStyle(color: AppColors.primaryGreen)),
              ),
          ],
        ),
      ),
    );
  }

  Future<void> _requestRenewal(BuildContext context) async {
    try {
      await ApiClient.dio.post('/subscriptions/${sub.id}/request-renewal');
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Renewal request sent to field owner')),
        );
      }
    } catch (e) {
      if (context.mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text('Error: $e')));
      }
    }
  }
}

class _StatusDot extends StatelessWidget {
  final String status;
  const _StatusDot(this.status);
  @override
  Widget build(BuildContext context) {
    final color = status == 'active'
        ? AppColors.primaryGreen
        : status == 'pending_payment'
            ? AppColors.warning
            : Colors.grey;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: color.withOpacity(0.12),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Text(status.replaceAll('_', ' '),
          style: TextStyle(
              fontSize: 11, color: color, fontWeight: FontWeight.w600)),
    );
  }
}
