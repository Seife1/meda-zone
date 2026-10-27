import 'package:flutter/material.dart';
import '../../core/theme.dart';

/// A friendly full-page error widget with an optional retry button.
/// Use instead of raw `Text('Error: $e')` in every screen.
class ErrorView extends StatelessWidget {
  final String message;
  final VoidCallback? onRetry;

  const ErrorView({
    super.key,
    this.message = 'Something went wrong. Please try again.',
    this.onRetry,
  });

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.error_outline, size: 56, color: AppColors.error),
            const SizedBox(height: 16),
            Text(
              message,
              textAlign: TextAlign.center,
              style: Theme.of(context)
                  .textTheme
                  .bodyLarge
                  ?.copyWith(color: AppColors.error),
            ),
            if (onRetry != null) ...[
              const SizedBox(height: 24),
              ElevatedButton.icon(
                onPressed: onRetry,
                icon: const Icon(Icons.refresh),
                label: const Text('Retry'),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

/// Extracts a user-friendly message from a Dio/server exception.
String friendlyErrorMessage(dynamic e) {
  try {
    final data = (e as dynamic).response?.data;
    if (data is Map) {
      final detail = data['detail'];
      if (detail is Map) return detail['message']?.toString() ?? 'An error occurred.';
      if (detail is String && detail.isNotEmpty) return detail;
    }
  } catch (_) {}
  // Fallback: strip the noisy DioException prefix
  final raw = e.toString();
  if (raw.contains('SocketException') || raw.contains('connection')) {
    return 'No internet connection. Please check your network and try again.';
  }
  if (raw.contains('timeout')) {
    return 'The request timed out. Please try again.';
  }
  return 'Something went wrong. Please try again.';
}
