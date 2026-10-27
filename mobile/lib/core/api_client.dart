import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'constants.dart';

class UnauthorizedException implements Exception {
  final String message;
  const UnauthorizedException([this.message = 'Session expired. Please log in again.']);

  @override
  String toString() => 'UnauthorizedException: $message';
}

class ApiClient {
  ApiClient._();
  static final ApiClient instance = ApiClient._();

  final _storage = const FlutterSecureStorage();
  late final Dio _dio = _buildDio();

  static Dio get dio => instance._dio;

  Dio _buildDio() {
    final dio = Dio(BaseOptions(
      baseUrl: AppConstants.apiBaseUrl,
      connectTimeout: const Duration(seconds: 10),
      receiveTimeout: const Duration(seconds: 15),
      headers: {'Content-Type': 'application/json'},
    ));

    dio.interceptors.add(InterceptorsWrapper(
      onRequest: (options, handler) async {
        final token = await _storage.read(key: AppConstants.kAccessToken);
        if (token != null) {
          options.headers['Authorization'] = 'Bearer $token';
        }
        handler.next(options);
      },
      onError: (error, handler) async {
        if (error.response?.statusCode == 401) {
          // Try token refresh
          final refreshToken =
              await _storage.read(key: AppConstants.kRefreshToken);
          if (refreshToken != null) {
            try {
              final refreshDio =
                  Dio(BaseOptions(baseUrl: AppConstants.apiBaseUrl));
              final resp = await refreshDio.post(
                '/auth/refresh',
                data: {'refresh_token': refreshToken},
              );
              final newToken = resp.data['access_token'] as String;
              await _storage.write(
                  key: AppConstants.kAccessToken, value: newToken);
              // Retry original request with new token
              error.requestOptions.headers['Authorization'] =
                  'Bearer $newToken';
              final retryResp = await dio.fetch(error.requestOptions);
              return handler.resolve(retryResp);
            } catch (_) {
              await _storage.deleteAll();
              return handler.reject(
                DioException(
                  requestOptions: error.requestOptions,
                  error: const UnauthorizedException(),
                  type: DioExceptionType.unknown,
                ),
              );
            }
          }
        }
        handler.next(error);
      },
    ));

    return dio;
  }
}
