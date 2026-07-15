{ lib
, buildPythonApplication
, setuptools
, flask
, sqlalchemy
, pillow
, gunicorn
}:

buildPythonApplication {
  pname = "ieri-oggi";
  version = "0.1.0";
  pyproject = true;

  src = lib.cleanSource ../.;

  build-system = [ setuptools ];

  dependencies = [
    flask
    sqlalchemy
    pillow
    gunicorn
  ];

  # Nessuna suite di test: si verifica guidando l'app.
  doCheck = false;

  meta = {
    description = "Ieri & Oggi — galleria di profili con foto da giovani e recenti";
    mainProgram = "ieri-oggi";
  };
}
