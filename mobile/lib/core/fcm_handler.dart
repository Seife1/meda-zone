import 'dart:convert';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/material.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:dio/dio.dart';
import 'constants.dart';
import 'api_client.dart';

// ── Notification channel config ───────────────────────────────────────────────
const _kChannelId          = 'medazone_bookings';
const _kChannelName        = 'MedaZone Bookings';
const _kChannelDescription = 'Booking confirmations, reminders, and updates';

const _kAlertChannelId          = 'medazone_alerts';
const _kAlertChannelName        = 'MedaZone Alerts';
const _kAlertChannelDescription = 'Urgent slot and subscription alerts';

// Singleton local notifications plugin (also used by main.dart background handler)
final FlutterLocalNotificationsPlugin localNotifications =
    FlutterLocalNotificationsPlugin();

// Navigation callback set by main.dart
/// Callback type for notification tap routing.
typedef NotificationRouteCallback = void Function(String route);

NotificationRouteCallback? _onNotificationTap;

// ── Public API ────────────────────────────────────────────────────────────────

/// Call once in [main] after Firebase.initializeApp().
/// [onTap] receives the route string to navigate to (e.g. '/bookings').
Future<void> initFcm({required NotificationRouteCallback onTap}) async {
  _onNotificationTap = onTap;

  // 1. Init local notifications plugin
  const initSettings = InitializationSettings(
    android: AndroidInitializationSettings('@mipmap/ic_launcher'),
    iOS: DarwinInitializationSettings(
      requestAlertPermission: false,
      requestBadgePermission: false,
      requestSoundPermission: false,
    ),
  );
  await localNotifications.initialize(
    initSettings,
    onDidReceiveNotificationResponse: _onLocalNotificationTap,
  );

  // 2. Create Android notification channels
  final androidImpl = localNotifications
      .resolvePlatformSpecificImplementation<
          AndroidFlutterLocalNotificationsPlugin>();

  await androidImpl?.createNotificationChannel(
    const AndroidNotificationChannel(
      _kChannelId,
      _kChannelName,
      description: _kChannelDescription,
      importance: Importance.high,
      playSound: true,
      enableVibration: true,
      enableLights: true,
    ),
  );

  await androidImpl?.createNotificationChannel(
    const AndroidNotificationChannel(
      _kAlertChannelId,
      _kAlertChannelName,
      description: _kAlertChannelDescription,
      importance: Importance.max,
      playSound: true,
      enableVibration: true,
      enableLights: true,
    ),
  );

  // 3. Request permission (iOS + Android 13+)
  final messaging = FirebaseMessaging.instance;
  final settings = await messaging.requestPermission(
    alert: true,
    badge: true,
    sound: true,
    provisional: false,
  );
  debugPrint('[FCM] Permission: ${settings.authorizationStatus}');

  // 4. Foreground message handler → show local notification
  FirebaseMessaging.onMessage.listen(_handleForegroundMessage);

  // 5. Background/terminated tap → navigate
  FirebaseMessaging.onMessageOpenedApp.listen(_handleNotificationOpenedApp);

  // 6. Check if app was launched from a terminated-state notification tap
  final initial = await messaging.getInitialMessage();
  if (initial != null) _handleNotificationOpenedApp(initial);

  // 7. Get & register token
  await refreshAndRegisterToken();

  // 8. Listen for token refreshes
  messaging.onTokenRefresh.listen((newToken) async {
    debugPrint('[FCM] Token refreshed');
    await _registerTokenWithBackend(newToken);
  });
}

/// Fetches the current FCM token and registers it with the backend.
/// Safe to call any time after [initFcm] (e.g. after login).
Future<void> refreshAndRegisterToken() async {
  try {
    final token = await FirebaseMessaging.instance.getToken();
    if (token == null) {
      debugPrint('[FCM] No token available (simulator / no Google Play?)');
      return;
    }
    debugPrint('[FCM] Token: ${token.substring(0, 20)}...');
    await _registerTokenWithBackend(token);
  } catch (e) {
    debugPrint('[FCM] refreshAndRegisterToken error: $e');
  }
}

/// Clears the FCM token from the backend on logout.
Future<void> deregisterToken() async {
  try {
    await ApiClient.dio.put(
      '/users/me/fcm-token',
      // Use empty string instead of null to satisfy non-nullable API contracts.
      data: {'fcm_token': ''},
    );
    debugPrint('[FCM] Token deregistered');
  } catch (e) {
    debugPrint('[FCM] deregisterToken error: $e');
  }
}

// ── Foreground handler ────────────────────────────────────────────────────────
Future<void> _handleForegroundMessage(RemoteMessage message) async {
  debugPrint('[FCM] Foreground message: ${message.messageId}');
  await showLocalNotification(message);
}

// ── Background / terminated tap handler ──────────────────────────────────────
void _handleNotificationOpenedApp(RemoteMessage message) {
  debugPrint('[FCM] Notification opened app: ${message.data}');
  final route = _routeFromData(message.data);
  _onNotificationTap?.call(route);
}

// ── Local notification tap (from showLocalNotification) ──────────────────────
void _onLocalNotificationTap(NotificationResponse response) {
  final payloadStr = response.payload;
  if (payloadStr == null || payloadStr.isEmpty) return;
  try {
    final data = jsonDecode(payloadStr) as Map<String, dynamic>;
    final route = _routeFromData(data);
    _onNotificationTap?.call(route);
  } catch (_) {}
}

// ── Display a local notification from a RemoteMessage ────────────────────────
Future<void> showLocalNotification(RemoteMessage message) async {
  final notification = message.notification;
  final title = notification?.title ??
      message.data['title'] as String? ??
      'MedaZone';
  final body =
      notification?.body ?? message.data['body'] as String? ?? '';
  final type = message.data['type'] as String? ?? '';

  // Use the alerts channel for time-sensitive types
  final isUrgent = type == 'slot_available' || type == 'booking_reminder';

  await localNotifications.show(
    message.hashCode,
    title,
    body,
    NotificationDetails(
      android: AndroidNotificationDetails(
        isUrgent ? _kAlertChannelId : _kChannelId,
        isUrgent ? _kAlertChannelName : _kChannelName,
        channelDescription: isUrgent
            ? _kAlertChannelDescription
            : _kChannelDescription,
        importance: isUrgent ? Importance.max : Importance.high,
        priority: Priority.high,
        icon: '@mipmap/ic_launcher',
        color: const Color(0xFF7DC832), // AppColors.primaryGreen
        enableVibration: true,
        playSound: true,
        styleInformation: BigTextStyleInformation(body),
      ),
      iOS: const DarwinNotificationDetails(
        presentAlert: true,
        presentBadge: true,
        presentSound: true,
      ),
    ),
    payload: jsonEncode(message.data),
  );
}

// ── Helpers ───────────────────────────────────────────────────────────────────

/// Maps FCM data payload `type` → in-app route.
String _routeFromData(Map<String, dynamic> data) {
  final type = data['type'] as String? ?? '';
  final bookingId = data['booking_id'] as String?;
  final subId = data['subscription_id'] as String?;
  final fieldId = data['field_id'] as String?;
  return switch (type) {
    'booking_confirmed'          => bookingId != null ? '/bookings/$bookingId' : '/bookings',
    'booking_reminder'           => bookingId != null ? '/bookings/$bookingId' : '/bookings',
    'booking_cancelled'          => '/bookings',
    'slot_available'             => fieldId != null ? '/fields/$fieldId' : '/map',
    'subscription_proposed'      => subId != null ? '/subscriptions/$subId' : '/subscriptions/manage',
    'subscription_activated'     => '/subscriptions/manage',
    'subscription_expiring_soon' => '/subscriptions/manage',
    'subscription_expired'       => '/subscriptions/manage',
    _                            => '/map',
  };
}

/// POST the token to the backend. Silently fails if not authenticated yet.
Future<void> _registerTokenWithBackend(String token) async {
  const storage = FlutterSecureStorage();
  final accessToken = await storage.read(key: AppConstants.kAccessToken);
  if (accessToken == null) {
    debugPrint('[FCM] Skipping registration — user not authenticated');
    return;
  }
  try {
    await ApiClient.dio.put(
      '/users/me/fcm-token',
      data: {'fcm_token': token},
      options: Options(receiveTimeout: const Duration(seconds: 8)),
    );
    debugPrint('[FCM] Token registered with backend');
  } catch (e) {
    debugPrint('[FCM] Backend registration failed: $e');
  }
}
