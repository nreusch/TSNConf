#=== Deal with inputs.
if ARGV.length < 5
	puts "saps_wrapper.rb is a wrapper for the SAPS algorithm."
	puts "Usage: ruby saps_wrapper.rb <instance_relname> <instance_specifics> <cutoff_time> <cutoff_length> <seed> <params to be passed on>."
	exit -1
end
testcase = ARGV[0]
tc_name = testcase.split("/")[-1].split(".")[0]

instance_specifics = ARGV[1]
cutoff_time = ARGV[2].to_i - 20
cutoff_length = ARGV[3].to_i
seed = ARGV[4].to_i
tstart = ARGV[12].to_i
alpha = ARGV[6].to_f
prmv = ARGV[10].to_f
k = ARGV[8].to_i
w = ARGV[14].to_i
#=== Here I assume instance_specifics only contains the desired target quality or nothing at all for the instance, but it could contain more (to be specified in the instance_file or instance_seed_file)
if instance_specifics == ""
	qual = 0
else
	qual = instance_specifics.split[0]
end

#paramstring = ARGV[5...ARGV.length].join(" ")


#=== Build algorithm command and execute it.
#cmd = "./../../optimizer #{paramstring} -r#{seed} -p#{cnf_filename} -t#{cutoff_time} -l#{cutoff_length} -c'SA' --returnWhenComplete"

cmd = "cd ../../TSNConf; source .venv/bin/activate; python3 -m main #{testcase} --mode SA_ROUTING_SA_SCHEDULING_COMB --aggregate #{tc_name}.csv --timeout_scheduling #{cutoff_time} --k #{k} --a 50000 --b 10000 --Tstart #{tstart} --alpha #{alpha}  --Prmv #{prmv} --w #{w}"

filename = "out_#{rand}.txt"
exec_cmd = "#{cmd} > ../paramILSConfig/#{tc_name}/#{filename}"

puts "Calling: #{exec_cmd}"
system exec_cmd

#=== Parse algorithm output to extract relevant information for ParamILS.
solved = 0
cost = -1

File.open("#{filename}"){|file|
	while line = file.gets
		if line =~ /Found Schedule/
			solved = 1
		end
		if line =~ /(\d+) Cost/
			cost = $1.to_i
		end
	end
}
puts "Result for ParamILS: SAT, -1, -1, #{cost}, #{seed}"
File.delete("#{tc_name}/#{filename}")
