import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import '../models/user_model.dart';

abstract class AuthLocalDataSource {
  Future<UserModel?> getCachedUser();
  Future<void> cacheUser(UserModel user);
  Future<void> clearCache();
  Future<String?> getAuthToken();
  Future<void> saveAuthToken(String token);
}

class AuthLocalDataSourceImpl implements AuthLocalDataSource {
  final SharedPreferences sharedPreferences;
  final FlutterSecureStorage secureStorage;

  static const String _userKey = 'CACHED_USER';
  static const String _tokenKey = 'AUTH_TOKEN';

  AuthLocalDataSourceImpl({
    required this.sharedPreferences,
    required this.secureStorage,
  });

  @override
  Future<UserModel?> getCachedUser() async {
    final jsonString = sharedPreferences.getString(_userKey);
    if (jsonString != null) {
      return UserModel.fromJson(json.decode(jsonString));
    }
    return null;
  }

  @override
  Future<void> cacheUser(UserModel user) async {
    await sharedPreferences.setString(
      _userKey,
      json.encode(user.toJson()),
    );
  }

  @override
  Future<void> clearCache() async {
    await sharedPreferences.remove(_userKey);
    await secureStorage.delete(key: _tokenKey);
  }

  @override
  Future<String?> getAuthToken() async {
    return await secureStorage.read(key: _tokenKey);
  }

  @override
  Future<void> saveAuthToken(String token) async {
    await secureStorage.write(key: _tokenKey, value: token);
  }
}