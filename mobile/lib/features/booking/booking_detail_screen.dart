import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:qr_flutter/qr_flutter.dart';
import '../../core/api_client.dart';
import '../../core/theme.dart';
import '../../shared/models/booking.dart';
import '../../shared/utils/date_format_utils.dart';

final _bookingDetailProvider =
    FutureProvider.family<Booking, String>((ref, bookingId) async {
  final resp = await ApiClient.dio.get('/bookings/$bookingId');
  return Booking.fromJson(resp.data as Map<String, dynamic>);
});

class BookingDetailScreen extends ConsumerWidget {
  final String bookingId;
  const BookingDetailScreen({super.key, required this.bookingId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final bookingAsync = ref.watch(_bookingDetailProvider(bookingId));

    return Scaffold(
      appBar: const BrandAppBar(),
      body: bookingAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => ErrorView(
          message: friendlyErrorMessage(e),
          onRetry: () => ref.refresh(_bookingDetailProvider(bookingId)),
        ),
        data: (booking) => SingleChildScrollView(
          padding: const EdgeInsets.all(20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              _InfoRow('Reference', booking.reference),
              _InfoRow('Date', formatSlotDate(booking.slotDate)),
              _InfoRow('Time', '${formatTime(booking.slotStartTime)} – ${formatTime(booking.slotEndTime)}'),
              _InfoRow('Status', booking.status),
              if (booking.cancellationReason != null)
                _InfoRow('Cancelled by', booking.cancellationReason!),
              const SizedBox(height: 24),
              Center(
                child: Column(
                  children: [
                    Text('QR Code for Check-In',
                        style: Theme.of(context).textTheme.titleMedium),
                    const SizedBox(height: 12),
                    QrImageView(
                      data: booking.reference,
                      version: QrVersions.auto,
                      size: 200,
                      backgroundColor: Colors.white,
                    ),
                    const SizedBox(height: 8),
                    Text(booking.reference,
                        style: Theme.of(context).textTheme.bodySmall?.copyWith(
                              fontFamily: 'monospace',
                              letterSpacing: 2,
                            )),
                  ],
                ),
              ),
              const SizedBox(height: 32),
              if (booking.status == 'confirmed')
                OutlinedButton.icon(
                  onPressed: () => _cancelBooking(context, ref, booking),
                  icon: const Icon(Icons.cancel_outlined, color: AppColors.error),
                  label: const Text('Cancel Booking',
                      style: TextStyle(color: AppColors.error)),
                  style: OutlinedButton.styleFrom(
                    side: const BorderSide(color: AppColors.error),
                    padding: const EdgeInsets.symmetric(vertical: 14),
                    shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(12)),
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }

  Future<void> _cancelBooking(
      BuildContext context, WidgetRef ref, Booking booking) async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('Cancel Booking?'),
        content: const Text('This cannot be undone. The slot will be released.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Keep')),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Cancel Booking', style: TextStyle(color: Colors.red)),
          ),
        ],
      ),
    );
    if (confirm == true && context.mounted) {
      try {
        await ApiClient.dio.delete('/bookings/${booking.id}');
        ref.invalidate(_bookingDetailProvider(bookingId));
        if (context.mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Booking cancelled')));
        }
      } catch (e) {
        if (context.mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Error: $e')));
        }
      }
    }
  }
}

class _InfoRow extends StatelessWidget {
  final String label;
  final String value;
  const _InfoRow(this.label, this.value);

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Row(
        children: [
          SizedBox(
            width: 100,
            child: Text(label,
                style: Theme.of(context)
                    .textTheme
                    .bodySmall
                    ?.copyWith(color: AppColors.textMuted)),
          ),
          Expanded(
            child: Text(value,
                style: Theme.of(context)
                    .textTheme
                    .bodyMedium
                    ?.copyWith(fontWeight: FontWeight.w600)),
          ),
        ],
      ),
    );
  }
}
