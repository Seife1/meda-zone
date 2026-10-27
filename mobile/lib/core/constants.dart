// App-wide constants
//
// Local dev: set DEV_HOST once in the repo root `.env`, then run:
//   ../scripts/run-mobile-dev.ps1
// or:
//   flutter run --dart-define=DEV_HOST=192.168.1.7
//
// Production builds override URLs explicitly:
//   flutter build apk --release \
//     --dart-define=API_BASE_URL=https://api.medazone.et/api/v1 \
//     --dart-define=WS_BASE_URL=wss://api.medazone.et
//
class AppConstants {
  AppConstants._();

  // Brand colors (also defined in theme.dart — kept here for non-widget use)
  static const int kPrimaryGreenValue = 0xFF7DC832;
  static const int kDarkGreenValue    = 0xFF1A5C2A;
  static const int kDarkNavyValue     = 0xFF1A1F3A;

  // API URLs (injected at build time via --dart-define)
  static const String devHost    = String.fromEnvironment('DEV_HOST', defaultValue: '127.0.0.1');
  static const String devApiPort = String.fromEnvironment('DEV_API_PORT', defaultValue: '8001');
  static const String _apiBaseOverride = String.fromEnvironment('API_BASE_URL');
  static const String _wsBaseOverride  = String.fromEnvironment('WS_BASE_URL');

  static String get apiBaseUrl => _apiBaseOverride.isNotEmpty
      ? _apiBaseOverride
      : 'http://$devHost:$devApiPort/api/v1';

  static String get wsBaseUrl => _wsBaseOverride.isNotEmpty
      ? _wsBaseOverride
      : 'ws://$devHost:$devApiPort';

  // Storage keys
  static const String kAccessToken  = 'access_token';
  static const String kRefreshToken = 'refresh_token';
  static const String kUserId       = 'user_id';
  static const String kUserRole     = 'user_role';
  static const String kFcmToken     = 'fcm_token';
  static const String kFilterPrefs  = 'filter_prefs';

  // Map defaults — Addis Ababa centre
  static const double defaultLat      = 9.005401;
  static const double defaultLng      = 38.763611;
  static const double defaultZoom     = 13.0;
  static const double searchRadiusKm  = 10.0;

  // WebSocket reconnect backoff
  static const int wsReconnectInitialMs = 2000;
  static const int wsReconnectMaxMs     = 30000;

  // Cache TTL
  static const int fieldCacheTtlMinutes = 10;
}
