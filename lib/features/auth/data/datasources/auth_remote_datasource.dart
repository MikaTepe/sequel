import '../../../../core/errors/exceptions.dart';
import '../../../../core/network/api_client.dart';
import '../models/user_model.dart';

abstract class AuthRemoteDataSource {
  Future<UserModel> login(String email, String password);
  Future<UserModel> signup(String email, String password, String? displayName);
  Future<void> logout();
  Future<UserModel?> getCurrentUser();
}

class AuthRemoteDataSourceImpl implements AuthRemoteDataSource {
  final ApiClient apiClient;

  AuthRemoteDataSourceImpl({required this.apiClient});

  @override
  Future<UserModel> login(String email, String password) async {
    // TODO: Implement API call to FastAPI backend
    // Example:
    // final response = await apiClient.dio.post('/auth/login', data: {
    //   'email': email,
    //   'password': password,
    // });
    // return UserModel.fromJson(response.data['user']);

    // Placeholder implementation
    await Future.delayed(const Duration(seconds: 1));
    return UserModel(
      id: 'user123',
      email: email,
      displayName: 'Test User',
    );
  }

  @override
  Future<UserModel> signup(String email, String password, String? displayName) async {
    // TODO: Implement API call to FastAPI backend
    // Example:
    // final response = await apiClient.dio.post('/auth/signup', data: {
    //   'email': email,
    //   'password': password,
    //   'display_name': displayName,
    // });
    // return UserModel.fromJson(response.data['user']);

    // Placeholder implementation
    await Future.delayed(const Duration(seconds: 1));
    return UserModel(
      id: 'user123',
      email: email,
      displayName: displayName ?? 'New User',
    );
  }

  @override
  Future<void> logout() async {
    // TODO: Implement API call to FastAPI backend
    // Example:
    // await apiClient.dio.post('/auth/logout');

    // Placeholder implementation
    await Future.delayed(const Duration(milliseconds: 500));
  }

  @override
  Future<UserModel?> getCurrentUser() async {
    // TODO: Implement API call to FastAPI backend
    // Example:
    // final response = await apiClient.dio.get('/auth/me');
    // return UserModel.fromJson(response.data);

    // Placeholder implementation - return null (no user logged in)
    return null;
  }
}