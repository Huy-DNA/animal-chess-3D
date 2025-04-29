{
  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system: let
      pkgs = nixpkgs.legacyPackages.${system};
    in {
      devShell = pkgs.mkShell {
        packages = with pkgs; [
          uv
          ruff
          python311
          python311Packages.pygame
          neovim
        ];
        shellHook = ''
          uv sync
        '';
      };
    });
}
