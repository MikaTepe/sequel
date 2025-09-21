import '../../domain/entities/user.dart';
import 'package:firebase_auth/firebase_auth.dart' as firebase_auth;

class UserModel extends User {
  const UserModel({
    required String id,
    required String email,
    String? displayName,
    String? photoUrl,
    bool emailVerified = false,
    DateTime? createdAt,
    DateTime? lastLoginAt,
  }) : super(
    id: id,
    email: email,
    displayName: displayName,
    photoUrl: photoUrl,
    emailVerified: emailVerified,
    createdAt: createdAt,
    lastLoginAt: lastLoginAt,
  );

  factory UserModel.fromJson(Map<String, dynamic> json) {
    return UserModel(
      id: json['id'],
      email: json['email'],
      displayName: json['displayName'],
      photoUrl: json['photoUrl'],
      emailVerified: json['emailVerified'] ?? false,
      createdAt: json['createdAt'] != null
          ? DateTime.parse(json['createdAt'])
          : null,
      lastLoginAt: json['lastLoginAt'] != null
          ? DateTime.parse(json['lastLoginAt'])
          : null,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'email': email,
      'displayName': displayName,
      'photoUrl': photoUrl,
      'emailVerified': emailVerified,
      'createdAt': createdAt?.toIso8601String(),
      'lastLoginAt': lastLoginAt?.toIso8601String(),
    };
  }

  factory UserModel.fromFirebaseUser(firebase_auth.User user) {
    return UserModel(
      id: user.uid,
      email: user.email ?? '',
      displayName: user.displayName,
      photoUrl: user.photoURL,
      emailVerified: user.emailVerified,
      createdAt: user.metadata.creationTime,
      lastLoginAt: user.metadata.lastSignInTime,
    );
  }
}