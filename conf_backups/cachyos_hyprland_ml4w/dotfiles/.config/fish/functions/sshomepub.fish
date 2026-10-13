function sshomepub --wraps ssh --description 'SSH to the home server through public DDNS'
    command ssh -o IdentitiesOnly=yes -i "$HOME/.ssh/mist_staging_key" ors@ors.strangled.net $argv
end
