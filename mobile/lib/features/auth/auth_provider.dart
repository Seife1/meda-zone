import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import '../../core/api_client.dart';
import '../../core/constants.dart';
import '../../shared/models/user.dart';

// ── Auth State ──────────────────────────────────────────────────────────────
class AuthState {
  final AppUser? user;
  final bool isLoading;
  final String? error;

  const AuthState({
    this.user,
    this.isLoading = false,
    this.error,
  });

  bool get isAuthenticated => user != null;

  AuthState copyWith({
    AppUser? user,
    bool? isLoading,
    String? error,
    bool clearUser = false,
    bool clearError = false,
  }) {
    return AuthState(
      user: clearUser ? null : (user ?? this.user),
      isLoading: isLoading ?? this.isLoading,
      error: clearError ? null : (error ?? this.error),
    );
  }
}

// ── Auth Notifier ────────────────────────────────────────────────────────────
class AuthNotifier extends StateNotifier<AuthState> {
  AuthNotifier() : super(const AuthState(isLoading: true)) {
    _restoreSession();
  }

  final _storage = const FlutterSecureStorage();
  final _api = ApiClient.dio;

  Future<void> _restoreSession() async {
    final token = await _storage.read(key: AppConstants.kAccessToken);
    if (token == null) {
      state = const AuthState();
      return;
    }
    try {
      final resp = await _api.get('/users/me');
      state = AuthState(user: AppUser.fromJson(resp.data as Map<String, dynamic>));
    } catch (_) {
      state = const AuthState();
    }
  }

  Future<void> register(String phone, String password, {String? displayName}) async {
    state = state.copyWith(isLoading: true, clearError: true);
    try {
      final resp = await _api.post('/auth/register', data: {
        'phone_number': phone,
        'password': password,
        if (displayName != null && displayName.isNotEmpty) 'display_name': displayName,
      });
      final data = resp.data as Map<String, dynamic>;
      await _storage.write(key: AppConstants.kAccessToken, value: data['access_token'] as String);
      await _storage.write(key: AppConstants.kRefreshToken, value: data['refresh_token'] as String);
      state = AuthState(user: AppUser.fromJson(data['user'] as Map<String, dynamic>));
    } catch (e) {
      state = state.copyWith(isLoading: false, error: _parseError(e));
      rethrow;
    }
  }

  Future<void> login(String phone, String password) async {
    state = state.copyWith(isLoading: true, clearError: true);
    try {
      final resp = await _api.post('/auth/login', data: {
        'phone_number': phone,
        'password': password,
      });
      final data = resp.data as Map<String, dynamic>;
      await _storage.write(key: AppConstants.kAccessToken, value: data['access_token'] as String);
      await _storage.write(key: AppConstants.kRefreshToken, value: data['refresh_token'] as String);
      state = AuthState(user: AppUser.fromJson(data['user'] as Map<String, dynamic>));
    } catch (e) {
      state = state.copyWith(isLoading: false, error: _parseError(e));
      rethrow;
    }
  }

  Future<void> updateProfile({String? displayName, List<String>? preferredPositions}) async {
    try {
      final resp = await _api.patch('/users/me', data: {
        if (displayName != null) 'display_name': displayName,
        if (preferredPositions != null) 'preferred_positions': preferredPositions,
      });
      state = AuthState(user: AppUser.fromJson(resp.data as Map<String, dynamic>));
    } catch (e) {
      throw Exception(_parseError(e));
    }
  }

  Future<void> logout() async {
    try {
      final refreshToken = await _storage.read(key: AppConstants.kRefreshToken) ?? '';
      await _api.post('/auth/logout', data: {'refresh_token': refreshToken});
    } catch (_) {}
    await _storage.deleteAll();
    state = const AuthState();
  }

  /// Fix #16: allows the UI to clear the error banner when the user starts typing.
  void clearError() {
    if (state.error != null) {
      state = state.copyWith(clearError: true);
    }
  }

  String _parseError(dynamic e) {
    try {
      final data = (e as dynamic).response?.data;
      if (data is Map) {
        final error = data['detail'];
        if (error is Map) return error['error']?['message']?.toString() ?? 'An error occurred';
        return error?.toString() ?? 'An error occurred';
      }
    } catch (_) {}
    return e.toString();
  }
}

final authProvider = StateNotifierProvider<AuthNotifier, AuthState>((ref) => AuthNotifier());
