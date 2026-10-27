import 'package:intl/intl.dart';

/// Formats an ISO date string (YYYY-MM-DD) into a human-readable form.
/// Examples:
///   "2026-07-06" → "Mon, Jul 6"
///   "2026-07-06" (today) → "Today, Jul 6"
///   "2026-07-07" (tomorrow) → "Tomorrow, Jul 7"
String formatSlotDate(String isoDate) {
  try {
    final date = DateTime.parse(isoDate);
    final now = DateTime.now();
    final today = DateTime(now.year, now.month, now.day);
    final d = DateTime(date.year, date.month, date.day);

    if (d == today) {
      return 'Today, ${DateFormat('MMM d').format(date)}';
    } else if (d == today.add(const Duration(days: 1))) {
      return 'Tomorrow, ${DateFormat('MMM d').format(date)}';
    } else {
      return DateFormat('EEE, MMM d').format(date);
    }
  } catch (_) {
    return isoDate; // fallback to raw string
  }
}

/// Formats a full ISO datetime string to "MMM d, yyyy".
String formatDate(String isoDate) {
  try {
    final date = DateTime.parse(isoDate);
    return DateFormat('MMM d, yyyy').format(date);
  } catch (_) {
    return isoDate;
  }
}

/// Formats a 24h time string (HH:mm:ss or HH:mm) to "h:mm a".
/// Example: "14:00" → "2:00 PM"
String formatTime(String timeStr) {
  try {
    // Accept HH:mm:ss or HH:mm
    final parts = timeStr.split(':');
    final h = int.parse(parts[0]);
    final m = int.parse(parts[1]);
    final dt = DateTime(2000, 1, 1, h, m);
    return DateFormat('h:mm a').format(dt);
  } catch (_) {
    return timeStr;
  }
}
