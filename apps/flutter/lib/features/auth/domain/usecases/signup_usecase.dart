import 'package:dartz/dartz.dart';
import 'package:equatable/equatable.dart';
import '../../../../core/errors/failures.dart';
import '../entities/user.dart';
import '../repositories/auth_repository.dart';

class SignupUseCase {
  final AuthRepository repository;

  SignupUseCase(this.repository);

  Future<Either<Failure, User>> call(SignupParams params) async {
    return await repository.signup(params.email, params.password, params.displayName);
  }
}

class SignupParams extends Equatable {
  final String email;
  final String password;
  final String? displayName;

  const SignupParams({
    required this.email,
    required this.password,
    this.displayName,
  });

  @override
  List<Object?> get props => [email, password, displayName];
}