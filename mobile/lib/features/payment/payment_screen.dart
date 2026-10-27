import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:url_launcher/url_launcher.dart';
import '../../core/api_client.dart';
import '../../core/theme.dart';
import '../../shared/models/subscription.dart';

final _paySubProvider = FutureProvider.family<Subscription, String>((ref, subId) async {
  final resp = await ApiClient.dio.get('/subscriptions/$subId');
  return Subscription.fromJson(resp.data as Map<String, dynamic>);
});

class PaymentScreen extends ConsumerStatefulWidget {
  final String subId;
  const PaymentScreen({super.key, required this.subId});
  @override
  ConsumerState<PaymentScreen> createState() => _PaymentScreenState();
}

class _PaymentScreenState extends ConsumerState<PaymentScreen> {
  String _provider = 'chapa';
  bool _paying = false;
  String? _error;

  Future<void> _pay(Subscription sub) async {
    setState(() { _paying = true; _error = null; });
    try {
      final resp = await ApiClient.dio.post(
        '/payments/$_provider/initialize',
        data: {'subscription_id': sub.id},
      );
      final url = _provider == 'chapa'
          ? resp.data['checkout_url'] as String
          : resp.data['payment_url'] as String;
      final uri = Uri.parse(url);
      if (await canLaunchUrl(uri)) {
        await launchUrl(uri, mode: LaunchMode.externalApplication);
      }
    } catch (e) {
      setState(() => _error = 'Payment failed: $e');
    } finally {
      if (mounted) setState(() => _paying = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final subAsync = ref.watch(_paySubProvider(widget.subId));
    return Scaffold(
      appBar: const BrandAppBar(),
      body: subAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => ErrorView(
          message: friendlyErrorMessage(e),
          onRetry: () => ref.refresh(_paySubProvider(widget.subId)),
        ),
        data: (sub) => Padding(
          padding: const EdgeInsets.all(20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text('Subscription Payment', style: Theme.of(context).textTheme.headlineMedium),
              const SizedBox(height: 8),
              Text('${sub.tier.replaceAll("_", " ")} · ${sub.totalSessions} sessions'),
              const SizedBox(height: 4),
              Text('ETB ${sub.totalPrice.toStringAsFixed(2)}',
                  style: const TextStyle(fontSize: 24, fontWeight: FontWeight.w800, color: AppColors.primaryGreen)),
              const SizedBox(height: 32),
              Text('Payment Method', style: Theme.of(context).textTheme.titleMedium),
              const SizedBox(height: 12),
              _ProviderChip(label: 'Chapa', value: 'chapa', selected: _provider == 'chapa',
                  onSelect: () => setState(() => _provider = 'chapa')),
              const SizedBox(height: 8),
              _ProviderChip(label: 'ArifPay', value: 'arifpay', selected: _provider == 'arifpay',
                  onSelect: () => setState(() => _provider = 'arifpay')),
              if (_error != null) ...[
                const SizedBox(height: 16),
                Text(_error!, style: const TextStyle(color: AppColors.error)),
              ],
              const Spacer(),
              PrimaryButton(
                label: 'Pay ETB ${sub.totalPrice.toStringAsFixed(0)}',
                isLoading: _paying,
                onPressed: _paying ? null : () => _pay(sub),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _ProviderChip extends StatelessWidget {
  final String label, value;
  final bool selected;
  final VoidCallback onSelect;
  const _ProviderChip({required this.label, required this.value, required this.selected, required this.onSelect});
  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onSelect,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
        decoration: BoxDecoration(
          color: selected ? AppColors.primaryGreen.withOpacity(0.08) : null,
          border: Border.all(color: selected ? AppColors.primaryGreen : Colors.grey.shade300),
          borderRadius: BorderRadius.circular(12),
        ),
        child: Row(
          children: [
            Icon(Icons.payment, color: selected ? AppColors.primaryGreen : Colors.grey),
            const SizedBox(width: 12),
            Text(label, style: TextStyle(fontWeight: selected ? FontWeight.w700 : FontWeight.normal)),
            const Spacer(),
            if (selected) const Icon(Icons.check_circle, color: AppColors.primaryGreen),
          ],
        ),
      ),
    );
  }
}
