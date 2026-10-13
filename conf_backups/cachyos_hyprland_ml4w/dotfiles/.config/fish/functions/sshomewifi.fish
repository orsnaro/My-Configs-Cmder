function sshomewifi --wraps ssh --description 'SSH to the home server over Wi-Fi'
    command ssh -o IdentitiesOnly=yes -i "$HOME/.ssh/mist_staging_key" ors@192.168.1.13 $argv
end
