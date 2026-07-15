{
  description = "Ieri & Oggi - galleria profili con foto da giovani e recenti";

  inputs.nixpkgs.url = "nixpkgs/nixos-26.05";
  inputs.flake-utils.url = "github:numtide/flake-utils";

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
      in
      {
        packages = rec {
          default = ieri-oggi;
          ieri-oggi = pkgs.python3Packages.callPackage ./nix/package.nix { };
        };

        apps.default = flake-utils.lib.mkApp {
          drv = self.packages.${system}.default;
        };

        devShells.default = pkgs.mkShell {
          packages = [
            (pkgs.python3.withPackages (ps: with ps; [
              flask
              sqlalchemy
              pillow
              gunicorn
            ]))
          ];

          shellHook = ''
            echo "Ieri & Oggi - devShell pronta."
            echo "Avvio sviluppo:  flask --app ieri_oggi.wsgi run --debug"
            echo "Apri:            http://127.0.0.1:5000"
          '';
        };
      }
    ) // {
      nixosModules.default = import ./nix/module.nix self;

      overlays.default = final: prev: {
        ieri-oggi = final.python3Packages.callPackage ./nix/package.nix { };
      };
    };
}
