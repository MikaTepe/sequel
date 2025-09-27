import 'package:equatable/equatable.dart';

class User extends Equatable {
  final String id;
  final String email;
  final String? displayName;
  final String? photoUrl;
  final bool emailVerified;
  final DateTime? createdAt;
  final DateTime? lastLoginAt;

  const User({
    required this.id,
    required this.email,
    this.displayName,
    this.photoUrl,
    this.emailVerified = false,
    this.createdAt,
    this.lastLoginAt,
  });

  @override
  List<Object?> get props => [
    id,
    email,
    displayName,
    photoUrl,
    emailVerified,
    createdAt,
    lastLoginAt,
  ];
}