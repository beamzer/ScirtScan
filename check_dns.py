###########################################################################################################
# if the website name doesn't resolve we can skip the other checks
# this check is only for logging purposes and is not visible in the dashboard overview
# 20240521
###########################################################################################################
import dns.resolver
def check_dns(website, outfile, logger):
    """
    Args:
    website (str): The website being checked.
    outfile (file object): The file to write output to.
    logger (function pointer): Function to print debug information.
    """

    logger(f"=== check_dns")

    try:       
        outfile.write("\n===========DNS Check\n")

        try:
            ipv4_answers = dns.resolver.resolve(website, 'A')  # check IPv4 addresses
            for answer in ipv4_answers:
                logger(answer.address)
                outfile.write(f"{answer.address} \n")

            try:
                ipv6_answers = dns.resolver.resolve(website, 'AAAA')  # check IPv6 addresses
                for answer in ipv6_answers:
                    logger(answer.address)
                    outfile.write(answer.address + "\n")
            except dns.resolver.NoAnswer:
                logger("no IPv6 addresses")
                outfile.write("no IPv6 addresses\n")

            try:
                cname_answers = dns.resolver.resolve(website, 'CNAME')  # check CNAMEs (aliases)
                for answer in cname_answers:
                    logger(f"cname: {answer.target.to_text()}")
                    outfile.write("cname: " + answer.target.to_text() + "\n")
            except dns.resolver.NoAnswer:
                logger("no CNAMEs")
                outfile.write("no CNAMEs\n")

            try:
                mx_answers = dns.resolver.resolve(website, 'MX')  # check MX (mail exchange) records
                for answer in mx_answers:
                    logger(f"mx: {answer.exchange.to_text()}")
                    outfile.write("mx: " + answer.exchange.to_text() + "\n")
            except dns.resolver.NoAnswer:
                logger("no MX records")
                outfile.write("no MX records\n")

            try:
                txt_answers = dns.resolver.resolve(website, 'TXT')  # check for TXT (text) records
                for answer in txt_answers:
                    for txt_string in answer.strings:
                        logger(f"TXT: {txt_string}")
                        outfile.write("TXT: " + txt_string.decode('utf-8') + "\n")
            except dns.resolver.NoAnswer:
                logger("no TXT records")
                outfile.write("no TXT records\n")

        except dns.resolver.NoNameservers as e:
            logger(f"DNS lookup for {website} failed with SERVFAIL")
            outfile.write(f"DNS lookup for {website} failed with SERVFAIL")
            return False
        except dns.resolver.NXDOMAIN:
            logger(f"NXDOMAIN; Website {website} not found")
            outfile.write(f"NXDOMAIN; Website {website} not found")
            return False
        except dns.resolver.LifetimeTimeout as e:
            print(f"DNS resolution for {website} failed due to lifetime timeout.")
            print(f"Error details: {e}")
            return False

    except Exception as e:
        print(f"check_dns; an error occurred: {e}")

    return True