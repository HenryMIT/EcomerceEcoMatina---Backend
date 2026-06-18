class CredencialesInvalidasError(Exception):
    """Correo o contrasena incorrectos."""


class CuentaNoVerificadaError(Exception):
    """La cuenta aun no fue verificada por correo electronico."""


class CorreoYaRegistradoError(Exception):
    """El correo electronico ya tiene una cuenta asociada."""


class IdentificacionYaRegistradaError(Exception):
    """La combinacion tipo+numero de identificacion ya existe."""


class TokenInvalidoOExpiradoError(Exception):
    """El token no existe, ya fue usado o su tiempo de vida expiro."""


class ContrasenaActualIncorrectaError(Exception):
    """La contrasena actual proporcionada no coincide con la almacenada."""


class UsuarioNoEncontradoError(Exception):
    """No existe un usuario con el identificador dado."""


class LimiteReenvioError(Exception):
    """Se supero el limite de reenvios del correo de verificacion (CU-07 FE-03)."""
