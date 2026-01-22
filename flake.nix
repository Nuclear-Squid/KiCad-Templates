{
  description = "Nix flake for the KiCad plugin development";
  inputs.nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";

  outputs = { self, nixpkgs }: let
    pkgs = nixpkgs.legacyPackages.x86_64-linux;
    self-pkgs = self.packages.x86_64-linux;
  in {
    devShells.x86_64-linux.default = pkgs.mkShell {
      buildInputs = with pkgs; [
        (python3.withPackages (py-pkgs: with py-pkgs; [ uv ]))
        kicad
      ];

      shellHook = "source .venv/bin/activate";
    };
  };
}
