# Locked public SwiftPM source snapshots

These regular-file ZIP archives contain only original public Git objects and authentic refs for the revisions listed in the root dependency-sources.json. They are committed vendored source inputs under the TReleaseKit manual's vendored arrangement; they are not runtime/verification data or cached compiler products.

All tracked source files, original file modes, symlink blobs and raw LICENSE/NOTICE files remain part of their original Git trees. The bare repository has an explicit shallow boundary at the locked commit, so unrelated upstream history is unnecessary. Original tag objects are retained. No upstream or TTermite remote tag is created or moved.

The inventory records source URL, version, exact commit and tree, authentic tags, archive bytes and SHA-256. scripts/release_dependencies.py verifies those fields and Git object integrity, makes separate copies per source clone, then restricts Git resolution to local file transport. The archive does not include HOME, Git credential settings, compiler products, tests or local verification receipts. The original Citadel and NIO-SSH patches remain in their existing vendor directories.

To inspect a snapshot, extract it into a fresh local folder and use git --git-dir <folder> fsck --full --strict, git --git-dir <folder> show HEAD:LICENSE.txt (or the upstream license filename), or clone its file URL. Never refresh a digest automatically during a build. A dependency update requires review and a new versioned source commit.
