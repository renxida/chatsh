{
  description = "Application packaged using poetry2nix";
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
    poetry2nix = {
      url = "github:nix-community/poetry2nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs = { self, nixpkgs, flake-utils, poetry2nix }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        inherit (poetry2nix.lib.mkPoetry2Nix { inherit pkgs; }) mkPoetryApplication defaultPoetryOverrides;

        customOverrides = defaultPoetryOverrides.extend (self: super: {
          # Add overrides only if the package exists in super
          maturin = if super ? maturin then super.maturin.overridePythonAttrs (old: {
            buildInputs = (old.buildInputs or []) ++ [ pkgs.rustc pkgs.cargo ];
          }) else null;

          tiktoken = if super ? tiktoken then super.tiktoken.overridePythonAttrs (old: {
            buildInputs = (old.buildInputs or []) ++ [ self.setuptools-rust pkgs.rustc pkgs.cargo ];
          }) else null;

          pydantic-core = if super ? pydantic-core then super.pydantic-core.overridePythonAttrs (old: {
            buildInputs = (old.buildInputs or []) ++ [ pkgs.rustc pkgs.cargo ];
          }) else null;
        });

        chatsh = mkPoetryApplication {
          projectDir = ./.;
          overrides = [ customOverrides ];
          preferWheels = true;
        };

      in {
        packages.default = chatsh;

        devShells.default = pkgs.mkShell {
          inputsFrom = [ chatsh ];
          packages = [ pkgs.poetry ];
        };
      }
    );
}
