import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:equatable/equatable.dart';
import '../../../../core/errors/failures.dart';
import '../../domain/entities/user.dart';
import '../../domain/usecases/login_usecase.dart';
import '../../domain/usecases/signup_usecase.dart';
import '../../domain/usecases/logout_usecase.dart';
import '../../domain/usecases/get_current_user_usecase.dart';

part 'auth_event.dart';
part 'auth_state.dart';

class AuthBloc extends Bloc<AuthEvent, AuthState> {
  final LoginUseCase loginUseCase;
  final SignupUseCase signupUseCase;
  final LogoutUseCase logoutUseCase;
  final GetCurrentUserUseCase getCurrentUserUseCase;

  AuthBloc({
    required this.loginUseCase,
    required this.signupUseCase,
    required this.logoutUseCase,
    required this.getCurrentUserUseCase,
  }) : super(AuthInitial()) {
    on<LoginEvent>(_onLogin);
    on<SignupEvent>(_onSignup);
    on<LogoutEvent>(_onLogout);
    on<CheckAuthStatusEvent>(_onCheckAuthStatus);
  }

  Future<void> _onLogin(LoginEvent event, Emitter<AuthState> emit) async {
    emit(AuthLoading());

    final result = await loginUseCase(
      LoginParams(email: event.email, password: event.password),
    );

    result.fold(
      (failure) => emit(AuthError(message: _mapFailureToMessage(failure))),
      (user) => emit(AuthAuthenticated(user: user)),
    );
  }

  Future<void> _onSignup(SignupEvent event, Emitter<AuthState> emit) async {
    emit(AuthLoading());

    final result = await signupUseCase(
      SignupParams(
        email: event.email,
        password: event.password,
        displayName: event.displayName,
      ),
    );

    result.fold(
      (failure) => emit(AuthError(message: _mapFailureToMessage(failure))),
      (user) => emit(AuthAuthenticated(user: user)),
    );
  }

  Future<void> _onLogout(LogoutEvent event, Emitter<AuthState> emit) async {
    emit(AuthLoading());

    final result = await logoutUseCase(); // nimmt keine Parameter an
    result.fold(
      (failure) => emit(AuthError(message: _mapFailureToMessage(failure))),
      (_) => emit(AuthUnauthenticated()),
    );
  }

  Future<void> _onCheckAuthStatus(
      CheckAuthStatusEvent event, Emitter<AuthState> emit) async {
    // Optional: Loading anzeigen, falls benötigt
    emit(AuthLoading());

    final result = await getCurrentUserUseCase();

    result.fold(
      (failure) => emit(AuthError(message: _mapFailureToMessage(failure))),
      (user) {
        if (user != null) {
          emit(AuthAuthenticated(user: user));
        } else {
          emit(AuthUnauthenticated());
        }
      },
    );
  }

  String _mapFailureToMessage(Failure failure) {
    // Passe die Mapping-Logik an deine Failure-Klassen an
    final type = failure.runtimeType.toString();
    switch (type) {
      case 'NetworkFailure':
        return 'Keine Internetverbindung';
      case 'ServerFailure':
        return 'Serverfehler aufgetreten';
      case 'CacheFailure':
        return 'Cachefehler aufgetreten';
      case 'AuthenticationFailure':
        return 'Authentifizierung fehlgeschlagen';
      default:
        return 'Unerwarteter Fehler ist aufgetreten';
    }
  }
}