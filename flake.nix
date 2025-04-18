{
  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs?ref=nixos-unstable";
  };

  outputs = { self, nixpkgs }: {
    packages.x86_64-linux.default =
      let
        pkgs = nixpkgs.legacyPackages.x86_64-linux;
        pypkgs = pkgs.python3Packages;
        simplejpeg = pypkgs.buildPythonPackage rec {
          pname = "simplejpeg";
          version = "1.8.2";
          buildInputs = [
            pkgs.libjpeg_turbo
          ];
          src = pkgs.fetchFromGitHub {
            owner = "jfolz";
            repo = "simplejpeg";
            rev = "c6051d5";
            hash = "sha256-SsDSJUUJQ5MjbOBNwVye4mn8yHBWvV9h0EYzTo4hGRc=";
          };
          dependencies = [ pypkgs.numpy ];
          patches = [ ./nix/simplejpeg.diff ];
        };
      in
      pypkgs.buildPythonApplication {
        name = "kvm-client";
        src = ./.;
        pyproject = true;
        dependencies = [
          pypkgs.click
          pypkgs.construct
          pypkgs.numpy
          pypkgs.pygame
          simplejpeg
        ];
        build-system = [ pypkgs.hatchling ];
      };

    devShells.x86_64-linux.default =
      let pkgs = nixpkgs.legacyPackages.x86_64-linux;
      in pkgs.mkShell {
        buildInputs = [ pkgs.uv ];
      };
  };
}
