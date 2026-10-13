function sshome --wraps ssh --description 'SSH to the home server over Ethernet'
    command ssh -o IdentitiesOnly=yes -i "$HOME/.ssh/mist_staging_key" ors@192.168.1.12 $argv
end
