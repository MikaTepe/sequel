import 'package:dio/dio.dart';

class ApiClient {
  final Dio dio;
  // TODO: Replace with your FastAPI backend URL
  static const String baseUrl = 'http://localhost:8000/api';

  ApiClient(this.dio) {
    dio.options = BaseOptions(
      baseUrl: baseUrl,
      connectTimeout: const Duration(seconds: 10),
      receiveTimeout: const Duration(seconds: 10),
      headers: {
        'Content-Type': 'application/json',
      },
    );
  }

  void setAuthToken(String token) {
    dio.options.headers['Authorization'] = 'Bearer $token';
  }
}