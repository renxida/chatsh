{
  description = "ChatSH - A CLI chat application";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
      in
      {
        packages.default = pkgs.python3Packages.buildPythonApplication {
          pname = "chatsh";
          version = "0.1.0";
          src = ./.;

          propagatedBuildInputs = with pkgs.python3Packages; [
            aiofiles
            openai
            anthropic
            tiktoken
            google-generativeai
          ];

          # If you have any build-time dependencies, add them here
          nativeBuildInputs = with pkgs.python3Packages; [
            # Add any build dependencies here
          ];

          # If you need to modify the build process, you can do so here
          # For example, to exclude tests:
          # doCheck = false;

          # To make the chatsh.py script executable:
          postInstall = ''
            chmod +x $out/bin/chatsh.py
            mv $out/bin/chatsh.py $out/bin/chatsh
          '';
        };

        apps.default = flake-utils.lib.mkApp {
          drv = self.packages.${system}.default;
        };

        devShells.default = pkgs.mkShell {
          buildInputs = with pkgs; [
            (python3.withPackages (ps: with ps; [
              aiofiles
              openai
              anthropic
              tiktoken
              google-generativeai
            ]))
          ];
        };
      }
    );
}