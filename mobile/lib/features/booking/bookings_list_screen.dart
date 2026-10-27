import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../core/api_client.dart';
import '../../core/local_db.dart';
import '../../core/theme.dart';
import '../../shared/models/booking.dart';
import '../../shared/utils/date_format_utils.dart';

final _bookingsProvider = FutureProvider<List<Booking>>((ref) async {
  final connectivity = await Connectivity().checkConnectivity();
  if (connectivity == ConnectivityResult.none) {
    final cached = await localDb.getBookings();
    return cached.map((j) => Booking.fromJson(j)).toList();
  }
  final resp = await ApiClient.dio.get('/bookings/me');
  final rawList = resp.data as List<dynamic>;
  await localDb.upsertBookings(rawList.cast<Map<String, dynamic>>());
  return rawList.map((j) => Booking.fromJson(j as Map<String, dynamic>)).toList();
});

class BookingsListScreen extends ConsumerWidget {
  const BookingsListScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final bookingsAsync = ref.watch(_bookingsProvider);

    return Scaffold(
      appBar: const BrandAppBar(),
      body: bookingsAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => ErrorView(
          message: friendlyErrorMessage(e),
          onRetry: () => ref.refresh(_bookingsProvider.future),
        ),
        data: (bookings) {
          if (bookings.isEmpty) {
            return const Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text('⚽', style: TextStyle(fontSize: 48)),
                  SizedBox(height: 12),
                  Text('No bookings yet'),
                  SizedBox(height: 4),
                  Text('Book a field to get started!',
                      style: TextStyle(color: AppColors.textMuted)),
                ],
              ),
            );
          }
          // Fix #9: confirmed + checked_in = upcoming; cancelled = past
          final upcoming = bookings
              .where((b) => b.status == 'confirmed' || b.status == 'checked_in')
              .toList();
          final cancelled = bookings.where((b) => b.status == 'cancelled').toList();
          final other = bookings
              .where((b) => b.status != 'confirmed' &&
                  b.status != 'checked_in' &&
                  b.status != 'cancelled')
              .toList();
          return RefreshIndicator(
            onRefresh: () => ref.refresh(_bookingsProvider.future),
            child: ListView(
              padding: const EdgeInsets.all(16),
              children: [
                if (upcoming.isNotEmpty) ...[
                  _SectionHeader('Upcoming (${upcoming.length})'),
                  ...upcoming.map((b) => _BookingCard(b)),
                ],
                if (cancelled.isNotEmpty) ...[
                  _SectionHeader('Cancelled'),
                  ...cancelled.map((b) => _BookingCard(b)),
                ],
                if (other.isNotEmpty) ...[
                  _SectionHeader('Other'),
                  ...other.map((b) => _BookingCard(b)),
                ],
              ],
            ),
          );
        },
      ),
    );
  }
}

class _SectionHeader extends StatelessWidget {
  final String title;
  const _SectionHeader(this.title);
  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 8),
        child: Text(title, style: Theme.of(context).textTheme.titleMedium),
      );
}

class _BookingCard extends StatelessWidget {
  final Booking booking;
  const _BookingCard(this.booking);

  @override
  Widget build(BuildContext context) {
    final statusColor = booking.status == 'confirmed'
        ? AppColors.primaryGreen
        : booking.status == 'checked_in'
            ? Colors.blue
            : Colors.grey;

    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: ListTile(
        onTap: () => context.go('/bookings/${booking.id}'),
        leading: const Icon(Icons.sports_soccer, color: AppColors.primaryGreen),
        title: Text(booking.reference, style: const TextStyle(fontWeight: FontWeight.w600)),
        subtitle: Text('${formatSlotDate(booking.slotDate)} · ${formatTime(booking.slotStartTime)}–${formatTime(booking.slotEndTime)}'),
        trailing: Container(
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
          decoration: BoxDecoration(
            color: statusColor.withOpacity(0.12),
            borderRadius: BorderRadius.circular(8),
          ),
          child: Text(
            booking.status,
            style: TextStyle(color: statusColor, fontSize: 11, fontWeight: FontWeight.w600),
          ),
        ),
      ),
    );
  }
}
