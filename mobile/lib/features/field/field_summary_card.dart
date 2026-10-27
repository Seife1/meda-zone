import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../core/theme.dart';
import '../../shared/models/field.dart';
import '../../shared/utils/date_format_utils.dart';

class FieldSummaryCard extends StatelessWidget {
  final Field field;
  const FieldSummaryCard({super.key, required this.field});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(20),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Handle
          Center(
            child: Container(
              width: 40, height: 4,
              decoration: BoxDecoration(
                color: Colors.grey[300],
                borderRadius: BorderRadius.circular(2),
              ),
            ),
          ),
          const SizedBox(height: 16),
          Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(field.name, style: Theme.of(context).textTheme.titleLarge),
                    if (field.distanceKm != null)
                      Text('${field.distanceKm!.toStringAsFixed(1)} km away',
                          style: Theme.of(context).textTheme.bodySmall),
                  ],
                ),
              ),
              if (field.isSponsored)
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: const Color(0xFFFFD700).withOpacity(0.15),
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: const Color(0xFFFFD700)),
                  ),
                  child: const Text('Sponsored',
                      style: TextStyle(fontSize: 11, color: Color(0xFFB8860B))),
                ),
            ],
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              _InfoChip(icon: Icons.grass, label: field.surfaceType),
              const SizedBox(width: 8),
              _InfoChip(
                icon: Icons.attach_money,
                label: 'ETB ${field.pricePerHour.toStringAsFixed(0)}/hr',
              ),
              if (field.averageRating > 0) ...[
                const SizedBox(width: 8),
                _InfoChip(
                  icon: Icons.star,
                  label: field.averageRating.toStringAsFixed(1),
                  iconColor: const Color(0xFFFFD700),
                ),
              ],
            ],
          ),
          if (field.nextAvailableSlot != null) ...[
            const SizedBox(height: 12),
            Row(
              children: [
                const Icon(Icons.access_time, size: 16, color: AppColors.primaryGreen),
                const SizedBox(width: 4),
                Text(
                  'Next: ${formatSlotDate(field.nextAvailableSlot!.slotDate)} · ${formatTime(field.nextAvailableSlot!.startTime)}',
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: AppColors.primaryGreen,
                        fontWeight: FontWeight.w600,
                      ),
                ),
              ],
            ),
          ],
          const SizedBox(height: 20),
          PrimaryButton(
            label: 'View Field',
            onPressed: () {
              Navigator.pop(context);
              context.go('/fields/${field.id}');
            },
          ),
          const SizedBox(height: 8),
        ],
      ),
    );
  }
}

class _InfoChip extends StatelessWidget {
  final IconData icon;
  final String label;
  final Color? iconColor;
  const _InfoChip({required this.icon, required this.label, this.iconColor});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(
        color: AppColors.primaryGreen.withOpacity(0.1),
        borderRadius: BorderRadius.circular(20),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 14, color: iconColor ?? AppColors.primaryGreen),
          const SizedBox(width: 4),
          Text(label,
              style: const TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.w600,
                  color: AppColors.darkNavy)),
        ],
      ),
    );
  }
}
