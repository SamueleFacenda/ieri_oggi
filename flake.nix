# nix comments
{
  description = "Allora & Oggi - galleria profili con foto da giovani e recenti";

  # Nixpkgs / NixOS version to use.
  inputs.nixpkgs.url = "nixpkgs/nixos-26.05";

  inputs.flake-utils.url = "github:numtide/flake-utils";

  outputs = { self, nixpkgs, flake-utils }:
    let
      version = "0.1.0";
      overlay = final: prev: { };
    in

    flake-utils.lib.eachDefaultSystem (system:
      let pkgs = (nixpkgs.legacyPackages.${system}.extend overlay); in
      {

        packages = rec {
          default = myPack;
          myPack = pkgs.stdenv.mkDerivation {
            pname = "myPack";
            src = pkgs.lib.cleanSource ./.;
            inherit version;

            nativeBuildInputs = with pkgs; [ ];

            buildPhase = ''
              '';

            installPhase = ''
              mkdir -p $out/bin
              cp * $out
            '';
          };
        };
        devShells = {
          default = pkgs.mkShell {
            inputsFrom = [ self.packages.${system}.default ];
            packages = with pkgs; [

              (python3.withPackages (ps: with ps; [
                flask
                sqlalchemy
                pillow
                gunicorn
              ]))
            ];

            shellHook = ''
              echo "Allora & Oggi - devShell pronta."
              echo "Avvio sviluppo:  flask --app app run --debug"
              echo "Apri:            http://127.0.0.1:5000"
            '';
          };

        };
      }
    );
}
