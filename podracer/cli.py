import json
import time
from collections import defaultdict

import click
import requests

from .affinity import affinity


def make_contact(contact):
    fn = contact.get("fn", "")
    email = contact.get("hasEmail", "")
    return [fn, email]


class Analyzer(object):
    """Analyze data.json objects for quality."""

    def __init__(self, verbose=False, link_check=False):
        self.by_identifier = defaultdict(list)
        self.by_title = defaultdict(list)
        self.keyword_counts = defaultdict(int)
        self.by_publisher = defaultdict(list)
        self.license_counts = defaultdict(int)
        self.program_counts = defaultdict(int)
        self.bureau_counts = defaultdict(int)
        self.contact_counts = defaultdict(int)
        self.access_level_counts = defaultdict(int)
        self.messages = []
        self.link_check = link_check
        self.verbose = verbose

    def analyze(self, dj):
        """Analyze a data.json object"""
        datasets = dj["dataset"]
        n_datasets = len(datasets)
        n_distributions = sum(len(ds.get("distribution", [])) for ds in datasets)

        # check for "ED CKAN" scraped metadata additions

        self.msg("Analysis of", dj.get("@id", "<missing @id>"))
        self.msg(n_datasets, "datasets", indent=1)
        self.msg(n_distributions, "distributions", indent=1)
        self.nl()

        if "source" in dj or "collection" in dj:
            n_sources = len(dj.get("source", []))
            n_collections = len(dj.get("collection", []))

            self.msg("Enhanced scraping metadata")
            self.msg(n_sources, "sources", indent=1)
            self.msg(n_collections, "collections", indent=1)
            self.nl()

        with click.progressbar(
            enumerate(datasets), length=n_datasets, label="Analyzing datasets"
        ) as bar:
            for index, dataset in bar:
                self.analyze_dataset(dataset, str(index))

    def analyze_dataset(self, ds, label):
        title = ds["title"]
        identifier = ds.get("identifier", "NONE")
        license = ds.get("license", "NONE")
        self.license_counts[license] += 1
        program = ds.get("programCode", ["NONE"])
        self.program_counts[tuple(program)] += 1
        bureau = ds.get("bureauCode", ["NONE"])
        self.bureau_counts[tuple(bureau)] += 1
        access_level = ds.get("accessLevel", "NONE")
        self.access_level_counts[access_level] += 1
        contact = make_contact(ds.get("contactPoint", "NONE"))
        self.contact_counts[tuple(contact)] += 1
        self.by_identifier[identifier].append(ds)
        self.by_title[title].append(ds)
        self.publish(ds, ds["publisher"])

        if self.verbose:
            self.msg("Dataset", label, title)

        landing_page = ds.get("landingPage", None)
        if landing_page and self.link_check:
            landing_page_check = self.check(landing_page)
            if landing_page_check:
                self.msg(
                    "Dataset", label, title, "- landingPage check", landing_page_check
                )

        keywords = ds.get("keyword", [])
        for keyword in keywords:
            self.keyword_counts[keyword] += 1
        self.analyze_distributions(ds, label)

    def analyze_distributions(self, ds, label):
        url_checks = []
        for d in ds.get("distribution", []):
            if self.verbose:
                # sigh
                title = d.get("title", d.get("Title", ""))
                self.msg("Distribution", title, indent=1)
            for k in ["downloadURL", "accessURL"]:
                if k in d:
                    url = d[k]
                    if self.link_check:
                        url_check = self.check(url)
                        if self.verbose:
                            self.msg(k, url, url_check if url_check else "OK", indent=2)
                        if url_check:
                            url_checks.append(url_check)
                    elif self.verbose:
                        self.msg(k, url, indent=2)
        if not self.verbose and url_checks:
            self.msg("Dataset", label, ds["title"], "has distribution problems:")
            for url_check in url_checks:
                self.msg(url_check, indent=1)

    def print_messages(self):
        for m in self.messages:
            print(m)

    def print_report(self):
        """Write an analysis report to stdout."""

        self.print_messages()
        self.report_duplicate_ids()
        self.report_duplicate_titles()
        self.report_questionable_keywords()
        self.report_counts()

    def report_duplicate_ids(self):
        print("Duplicate Identifiers")
        for identifier, ds in sorted(
            self.by_identifier.items(), key=lambda item: item[0]
        ):
            if len(ds) > 1:
                print("  Identifer:", identifier)
                for d in ds:
                    print("    Dataset:", d["title"])
        print("")

    def report_duplicate_titles(self):
        print("Duplicate Titles")
        for title, ds in sorted(self.by_title.items(), key=lambda item: item[0]):
            n_dups = len(ds)
            if n_dups > 1:
                print("  ", title, "[{} duplicates]".format(n_dups))
        print("")

    def report_questionable_keywords(self):
        def is_latin1(s):
            try:
                s.encode("latin-1")
                return True
            except Exception:
                return False

        print("Questionable Keywords")
        for keyword in sorted(self.keyword_counts.keys()):
            if len(keyword.split(" ")) > 6:
                print('  "{0}" - contains too many words?'.format(keyword))
            elif len(keyword) > 64:
                print('  "{0}" - too long?'.format(keyword))
            if '"' in keyword:
                print('  "{0}" - contains a double quote'.format(keyword))
            if not is_latin1(keyword):
                print('  "{0}" - contains non Latin-1 characters'.format(keyword))
        print("")

    def report_counts(self):
        print("Keyword counts")
        for keyword in sorted(self.keyword_counts.keys(), key=lambda k: k.casefold()):
            print('  "{0}" {1}'.format(keyword, self.keyword_counts[keyword]))
        print("")

        print("License counts")
        for license in sorted(self.license_counts.keys()):
            print("  {0} {1}".format(license, self.license_counts[license]))
        print("")

        print("Program counts")
        for program in sorted(self.program_counts.keys()):
            print("  {0} {1}".format(", ".join(program), self.program_counts[program]))
        print("")

        print("Bureau counts")
        for bureau in sorted(self.bureau_counts.keys()):
            print("  {0} {1}".format(", ".join(bureau), self.bureau_counts[bureau]))
        print("")

        print("Access Level counts")
        for access_level in sorted(self.access_level_counts.keys()):
            print(
                "  {0} {1}".format(access_level, self.access_level_counts[access_level])
            )
        print("")

        print("Contact Point counts")
        for contact in sorted(self.contact_counts.keys()):
            print("  {0} {1}".format(" ".join(contact), self.contact_counts[contact]))
        print("")

        print("Publisher counts")
        for publisher, ds in sorted(
            self.by_publisher.items(), key=lambda item: item[0]
        ):
            print("  {0} {1}".format(" > ".join(publisher), len(ds)))
        print("")

    def msg(self, *s, **kwargs):
        indent = kwargs.get("indent", 0)
        self.messages.append(("  " * indent) + " ".join(str(s0) for s0 in s))

    def nl(self):
        self.messages.append("")

    def check(self, url):
        time.sleep(0.5)
        try:
            r = requests.head(url, timeout=15.0)
            if not r.ok:
                return "{0} - HTTP ERROR {1}".format(url, r.status_code)
            else:
                return None
        except requests.exceptions.SSLError:
            return None
        except requests.exceptions.Timeout:
            return "{0} - REQUEST TIMEOUT".format(url)
        except requests.exceptions.ConnectionError:
            return "{0} - CONNECTION TIMEOUT".format(url)

    def publisher_path(self, publisher):
        # this shouldn't happen, but I've found some data.json in the world
        # where publishers are strings :-(
        if isinstance(publisher, str):
            return [publisher]
        sub_organizations = publisher.get("subOrganizationOf", None)
        name = publisher["name"]
        if not sub_organizations:
            return [name]
        else:
            return [name] + self.publisher_path(sub_organizations)

    def publish(self, ds, publisher):
        path = tuple(reversed(self.publisher_path(publisher)))
        self.by_publisher[path].append(ds)


@click.command()
@click.option(
    "--verbose", is_flag=True, help="Show more details about datasets and distributions"
)
@click.option(
    "--link-check",
    is_flag=True,
    help="Check dataset landing page and distribution URLs",
)
@click.option(
    "--keyword-cluster",
    is_flag=True,
    help="Enable (VERY) experimental keyword clustering."
    "  Not great, and slow for large # of keywords.",
)
@click.option("--no-verify", is_flag=True, help="Disable SSL verification")
@click.option("--url", help="URL to data.json endpoint")
@click.option(
    "-f",
    "--file",
    "file_",
    type=click.File("r"),
    help="Path to local data.json format file",
)
def main(url, file_, verbose, link_check, keyword_cluster, no_verify):
    # must have URL or file, but not both
    if not (url or file_):
        raise click.ClickException("must specify either --url or --file")
    if url and file_:
        raise click.ClickException("can't specify both --url and --file")

    dj = {}

    if url:
        resp = requests.get(url, verify=not no_verify)
        resp.raise_for_status()
        dj = resp.json()
    if file_:
        dj = json.load(file_)

    analyzer = Analyzer(verbose=verbose, link_check=link_check)
    analyzer.analyze(dj)
    analyzer.print_report()

    if keyword_cluster:
        print("Keyword Clusters")
        clusters = affinity(analyzer.keyword_counts)
        for exemplar in sorted(clusters.keys()):
            print('  {0}: "{1}"'.format(exemplar, '", "'.join(clusters[exemplar])))
        print("")


if __name__ == "__main__":
    main()
