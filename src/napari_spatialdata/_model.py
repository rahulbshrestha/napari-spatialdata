from typing import Any, Tuple, Union, Optional
from dataclasses import field, dataclass

from anndata import AnnData
from napari.layers import Layer
from napari.utils.events import Event, EmitterGroup
import numpy as np
import napari
import pandas as pd

from napari_spatialdata._utils import NDArrayA, _ensure_dense_vector
from napari_spatialdata._constants._constants import Symbol
from napari_spatialdata._constants._pkg_constants import Key

__all__ = ["ImageModel"]


@dataclass
class ImageModel:
    """Model which holds the data for interactive visualization."""

    events: EmitterGroup = field(init=False, default=None, repr=True)
    _layer: Layer = field(init=False, default=None, repr=True)
    _adata: AnnData = field(init=False, default=None, repr=True)
    _spatial_key: str = field(default=Key.obsm.spatial, repr=False)
    _label_key: str = field(default=None, repr=True)

    # library_key: Optional[str] = None
    library_id: str = field(init=False, default=None, repr=False)
    spot_diameter: Union[NDArrayA, float] = field(init=False, default=1)
    scale_key: str = field(init=False, default="tissue_hires_scalef")
    scale: float = field(init=False, default=None)
    coordinates: NDArrayA = field(init=False, default=None, repr=False)
    adata_layer: str = field(init=False, default=None, repr=False)
    palette: Optional[str] = field(init=False, default=None, repr=False)
    cmap: str = field(init=False, default="viridis", repr=False)
    blending: str = field(init=False, default="opaque", repr=False)
    key_added: str = "shapes"
    symbol: Union[Symbol, str] = Symbol.DISC

    def __post_init__(self) -> None:
        self.events = EmitterGroup(
            source=self,
            layer=Event,
            adata=Event,
        )

    # self.adata = self.layer.metadata["adata"]
    # self.library_id = self.layer.metadata["library_id"]

    # _assert_spatial_basis(self.adata, self.spatial_key)

    # self.symbol = Symbol(self.symbol)
    # if not self.adata.n_obs:
    #     raise ValueError("No spots were selected. Please ensure that the image contains at least 1 spot.")
    # self.coordinates = self.adata.obsm[self.spatial_key][:, ::-1][:, :2].copy()
    # self.scale = 1
    # # self._update_coords()

    # if TYPE_CHECKING:
    #     assert isinstance(self.library_id, Sequence)

    # try:
    #     self.container = Container._from_dataset(self.container.data.sel(z=self.library_id), deep=None)
    # except KeyError:
    #     raise KeyError(
    #         f"Unable to subset the image container with library ids `{self.library_id}`. "
    #         f"Valid library ids are `{self.container.library_ids}`."
    #     ) from None

    # @property
    # def layer(self) -> Optional[napari.layers.Labels]:
    #     return self._layer

    # @layer.setter
    # def layer(self, layer: Optional[napari.layers.Layer]):
    #     self._layer = layer
    #     self.events.layer()

    @property
    def layer(self) -> Optional[napari.layers.Labels]:
        """Get layer."""
        return self._layer

    @layer.setter
    def layer(self, layer: Optional[napari.layers.Layer]):
        self._layer = layer
        self.events.layer()

    @property
    def adata(self) -> Optional[AnnData]:
        """Get adata."""
        return self._adata

    @adata.setter
    def adata(self, adata: Optional[AnnData]):
        self._adata = adata
        self.events.adata()

    @property
    def adata_layer(self) -> str:
        """Get adata layer."""
        return self._adata_layer

    @adata_layer.setter
    def adata_layer(self, adata_layer: str):
        self._adata_layer = adata_layer

    @property
    def coordinates(self) -> NDArrayA:
        """Get coordinates."""
        return self._coordinates

    @coordinates.setter
    def coordinates(self, coordinates: NDArrayA):
        self._coordinates = coordinates

    @property
    def scale(self) -> float:
        """Get scale."""
        return self._scale

    @scale.setter
    def scale(self, scale: float):
        self._scale = scale

    @property
    def spot_diameter(self) -> NDArrayA:
        """Get spot diameter."""
        return self._spot_diameter

    @spot_diameter.setter
    def spot_diameter(self, spot_diameter: NDArrayA):
        self._spot_diameter = spot_diameter

    @property
    def labels_key(self) -> NDArrayA:
        """Get labels key."""
        return self._labels_key

    @labels_key.setter
    def labels_key(self, labels_key: str):
        self._labels_key = labels_key

    @_ensure_dense_vector
    def get_obs(self, name: str, **_: Any) -> Tuple[Optional[Union[pd.Series, NDArrayA]], str]:
        """
        Return an observation.

        Parameters
        ----------
        name
            Key in :attr:`anndata.AnnData.obs` to access.

        Returns
        -------
        The values and the formatted ``name``.
        """
        if name not in self.adata.obs.columns:
            raise KeyError(f"Key `{name}` not found in `adata.obs`.")
        return self.adata.obs[name], self._format_key(name)

    @_ensure_dense_vector
    def get_var(self, name: Union[str, int], **_: Any) -> Tuple[Optional[NDArrayA], str]:  # TODO(giovp): fix docstring
        """
        Return a gene.

        Parameters
        ----------
        name
            Gene name in :attr:`anndata.AnnData.var_names` or :attr:`anndata.AnnData.raw.var_names`,
            based on :paramref:`raw`.

        Returns
        -------
        The values and the formatted ``name``.
        """
        try:
            ix = self.adata._normalize_indices((slice(None), name))
        except KeyError:
            raise KeyError(f"Key `{name}` not found in `adata.var_names`.") from None

        return self.adata._get_X(layer=self.adata_layer)[ix], self._format_key(name, adata_layer=True)

    def get_items(self, attr: str) -> Tuple[str, ...]:
        """
        Return valid keys for an attribute.

        Parameters
        ----------
        attr
            Attribute of :mod:`anndata.AnnData` to access.

        Returns
        -------
        The available items.
        """
        adata = self.adata
        if attr in ("obs", "obsm"):
            return tuple(map(str, getattr(adata, attr).keys()))
        return tuple(map(str, getattr(adata, attr).index))

    @_ensure_dense_vector
    def get_obsm(self, name: str, index: Union[int, str] = 0) -> Tuple[Optional[NDArrayA], str]:
        """
        Return a vector from :attr:`anndata.AnnData.obsm`.

        Parameters
        ----------
        name
            Key in :attr:`anndata.AnnData.obsm`.
        index
            Index of the vector.

        Returns
        -------
        The values and the formatted ``name``.
        """
        if name not in self.adata.obsm:
            raise KeyError(f"Unable to find key `{name!r}` in `adata.obsm`.")
        res = self.adata.obsm[name]
        pretty_name = self._format_key(name, index=index)

        if isinstance(res, pd.DataFrame):
            try:
                if isinstance(index, str):
                    return res[index], pretty_name
                if isinstance(index, int):
                    return res.iloc[:, index], self._format_key(name, index=res.columns[index])
            except KeyError:
                raise KeyError(f"Key `{index}` not found in `adata.obsm[{name!r}].`") from None

        if not isinstance(index, int):
            try:
                index = int(index, base=10)
            except ValueError:
                raise ValueError(
                    f"Unable to convert `{index}` to an integer when accessing `adata.obsm[{name!r}]`."
                ) from None
        res = np.asarray(res)

        return (res if res.ndim == 1 else res[:, index]), pretty_name

    def _format_key(
        self, key: Union[str, int], index: Optional[Union[int, str]] = None, adata_layer: bool = False
    ) -> str:
        if index is not None:
            return str(key) + f":{index}:{self.layer}"
        if adata_layer:
            return str(key) + (f":{self.adata_layer}" if self.adata_layer is not None else ":X") + f":{self.layer}"

        return str(key) + (f":{self.layer}" if self.layer is not None else ":X")
