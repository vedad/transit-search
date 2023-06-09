#!/usr/bin/env python

from pathlib import Path
from astropy.io import fits
import numpy as np
import re

# __all__ = [
#     "Lightcurve", "LightcurveInjected", "Pathfinder", "_split_injected_lightcurve"
#     ]

__all__ = [
    "Lightcurve", "Pathfinder"
    ]

class Pathfinder:
    """
    Class for holding the path to a single TESS-SPOC `lightcurve` file. 
    """
    def __init__(self, tic=None, sector=None, provenance="tess-spoc", product="hlsp", mission="tess", version="v1", instrument="phot", data_path="/Users/u2271802/Data/tess/tess-spoc_ffi"):

        if tic is None:
            raise ValueError("`tic` number needs to be specified")

        self.data_path = data_path
        # if isinstance(tic, list):
            # tic = tic[0]
            
        # needed for file/directory structure
        self.tic_id = Pathfinder._create_padded_id(tic, 16)
        ticid_parts = [self.tic_id[i:i+4] for i in range(0, 16, 4)]
        self._ticid_parts_path = "/".join(ticid_parts)
        self.tic = tic
        self.provenance = provenance
        self.product = product
        self.mission = mission
        self.version = version
        self.instrument = instrument

        if sector is not None:
            self.filepaths = [self._get_sector_filepath(x) for x in sector]
        else:
            self.filepaths = self._get_all_filepaths()

        self.sectors = self._get_all_sectors()

        # if sector is not None:
        #     self.sectors = sector
        # else:
        #     self.sectors = self._get_all_sectors()

        # self.filepaths = [self._get_sector_filepath(s) for s in self.sectors]
    
    def _get_sector_filename(self, sector):
        sector_id = Pathfinder._create_padded_id(sector, 4)
        base_filename = (
            f"{self.product}_{self.provenance}_{self.mission}_{self.instrument}_{self.tic_id}-s{sector_id}_{self.mission}_{self.version}"
        )

        return f"{base_filename}_lc.fits"

    def _get_sector_filepath(self, sector):
        # sector_id4 = Pathfinder._create_padded_id(sector, 4)

        # base_filename = (
            # f"{self.product}_{self.provenance}_{self.mission}_{self.instrument}_{self.tic_id}-s{sector_id4}_{self.mission}_{self.version}"
        # )

        sector_id = Pathfinder._create_padded_id(sector, 2)
        filename = self._get_sector_filename(sector)
        filepath = Path(
            self.data_path, f"S{sector_id}", "target", 
            self._ticid_parts_path, filename
            )
        # filepath = Path(
        #     self.data_path, "_".join([base_filename, "tp"]), filename
        #                 ).as_posix()

        return filepath.as_posix()

    def _get_all_sectors(self):
        # filepaths = sorted(
        #     list(
        #         Path(self.data_path).glob(
        #             f"*{self.tic_id}*"
        #             )
        #         )
        #     )

        matches = [
            re.search("s00[0-9][0-9]", Path(x).name).group() for x in self.filepaths
            ]
        sectors = [x.lstrip("s00") for x in matches]
        return sectors
    
    def _get_all_filepaths(self):
        # "/storage/astro2/phsrmj/TESS/SPOC_30min/Sxx/target"

        p = Path(self.data_path)
        # ticid_parts = [self.tic_id[i:i+4] for i in range(0, 16, 4)]
        # ticid_parts_path = "/".join(ticid_parts)

        # search all sector subdirectories matching the 4-part 16-digit TIC
        matches = list(p.glob(f"S*/target/{self._ticid_parts_path}/*lc.fits"))

        # sort files by sector - bit convoluted because want to make sure it is sorted using the sector identifier in the filename and not the base directory structure
        sorted_idx = np.argsort([x.name for x in matches])
        filepaths = [matches[i].as_posix() for i in sorted_idx]
        
        return filepaths

    @staticmethod
    def _create_padded_id(input, output_length):
        # adds leading zeros to `input` until `output_lenght` is reached
        return f'{int(input):0{output_length}}'
    
    def _create_savedir2(self, basedir, sde, candidate):
        sector_ids = [Pathfinder._create_padded_id(s, 4) for s in self.sectors]
        sector_string = "-".join([f"s{x}" for x in sector_ids])
        return Path(
            basedir,
            self._ticid_parts_path,
            f"tls_{self.tic_id}.0{candidate}-{sector_string}_sde={sde:.1f}.pickle"
            )
    
    def _create_savedir(self, basedir, sde, candidate):
        sector_ids = [Pathfinder._create_padded_id(s, 4) for s in self.sectors]
        sector_string = "-".join([f"s{x}" for x in sector_ids])
        return Path(
            basedir, 
            f"tls_{self.tic_id}.0{candidate}-{sector_string}_sde={sde:.1f}.pickle"
            )

class Lightcurve:
    """
    Class for holding the light curve data for a single TESS-SPOC `lightcurve` file
    """
    def __init__(self, filepath, **kwargs):
        self._read_data(filepath, **kwargs)
        
    def _read_data(self, filepath, quality_flag=0):
        hdu = fits.open(filepath)

        self.header = hdu[0].header
    
        # self.tic     = hdu[0].header["TICID"]
        self.sector  = hdu[0].header["SECTOR"]
        self.ccd     = hdu[0].header["CCD"]
        self.camera  = hdu[0].header["CAMERA"]
        self.elapsed_time = hdu[1].header["TELAPSE"]

        # select data by quality and normalize
        m_quality = hdu[1].data["QUALITY"] == quality_flag
        m_nan = (
                np.isfinite(hdu[1].data["PDCSAP_FLUX_ERR"]) &
                np.isfinite(hdu[1].data["PDCSAP_FLUX"]) &
                np.isfinite(hdu[1].data["TIME"])
        )
        m_zero = (np.isclose(hdu[1].data["PDCSAP_FLUX_ERR"], 0) |
                  np.isclose(hdu[1].data["PDCSAP_FLUX"], 0)
        )
        m = m_quality & m_nan & ~m_zero
        self.time = hdu[1].data["TIME"][m]
        flux = hdu[1].data["PDCSAP_FLUX"][m]

        self.flux_err = hdu[1].data["PDCSAP_FLUX_ERR"][m] / np.median(flux)
        self.flux = flux / np.median(flux)

if __name__ == "__main__":

    pass
    # import matplotlib.pyplot as plt

    # data_dir = "/Users/u2271802/Astronomy/projects/neptunes/tess-neptune-search/transit-search/example_data"

    # lcpath = _get_filepath(data_dir, tic=21371, sector=11)

    # lc = Pathfinder(data_dir, tic=21371)
    # print(lc.tic_id)
    # print(lc.sectors)
    # print(lc.filepaths)

    # plt.errorbar(lc.time, lc.flux, yerr=lc.flux_err, capsize=0, fmt='.')
    # plt.show()
