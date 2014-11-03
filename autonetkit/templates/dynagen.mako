autostart = False
version = 0.8.3.1
[${topology.hypervisor_server}:${topology.hypervisor_port}]
    workingdir = /tmp
    udp = 10000
    [[7200]]
        image = ${topology.image}
        idlepc = ${topology.idlepc}
        ghostios = True

    %for router in topology.routers:
    [[ROUTER ${router.hostname}]]
        model = ${router.model}
        console = ${router.console}
        aux = ${router.aux}
        % for index, card in router.slots:
        slot${index} = PA-2FE-TX
        %endfor
        % for interface in router.interfaces:
        ${interface['src_port']} = ${interface['dst']} ${interface['dst_port']}
        %endfor
        x = ${router.x}
        y = ${router.y}
        z = 1.0
        cnfg = ${router.cnfg}
    %endfor

[GNS3-DATA]
    configs = ${topology.config_dir}

