{
  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs?ref=nixos-unstable";
  };

  outputs = { self, nixpkgs }: {
    packages.x86_64-linux.default =
      let
        pkgs = nixpkgs.legacyPackages.x86_64-linux;
        pypkgs = pkgs.python3Packages;
      in
      pypkgs.buildPythonApplication {
        name = "kvm-client";
        src = ./.;
        pyproject = true;
        dependencies = [ pypkgs.click pypkgs.construct pypkgs.pygame ];
        build-system = [ pypkgs.hatchling ];
      };

    devShells.x86_64-linux.default =
      let pkgs = nixpkgs.legacyPackages.x86_64-linux;
      in pkgs.mkShell {
        buildInputs = [ pkgs.uv ];
      };
  };
}
