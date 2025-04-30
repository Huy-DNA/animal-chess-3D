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
          stdenv.cc.cc.lib
          uv
          ruff
          python311
          python311Packages.numpy
          neovim
          xorg.libX11
          xorg.libXext
          xorg.libXrender
          xorg.libXcomposite
          xorg.libXfixes
          xorg.libXdamage
          mesa
          libGL
          openal
          alsa-lib
          libpulseaudio
        ];
        shellHook = ''
          uv sync
        '';
        LD_LIBRARY_PATH = "${pkgs.lib.makeLibraryPath [
          pkgs.libGL
          pkgs.xorg.libX11
          pkgs.mesa
          pkgs.stdenv.cc.cc.lib
          pkgs.libpulseaudio
          pkgs.alsa-lib
        ]}" ;
      };
    });
}
