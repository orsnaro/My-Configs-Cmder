# Historical network-test baseline

`before-network/*.jsonc` are the original configurations from repository commit
`26ace17` (before the October network-query refresh), not copies of the code under
test. They replace the original developer's disposable `/tmp` fixture directory.
The later, deliberate default ASCII logo, CPU/board label and mounted-volume
query are checked explicitly by the test; all other non-network fields remain
compared with these historical files. No production Fastfetch setting is changed.
